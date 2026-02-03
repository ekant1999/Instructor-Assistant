"""
Migration script to transfer data from SQLite to PostgreSQL with pgvector support.

This script:
1. Reads existing data from SQLite database
2. Transforms and inserts into PostgreSQL tables
3. Preserves all relationships and metadata
4. Handles large datasets in batches
"""
import sys
import asyncio
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
import asyncpg

# Add backend to path
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from core.database import DB_PATH
from core.postgres import DATABASE_URL, init_db


BATCH_SIZE = 1000


async def migrate_papers(sqlite_conn: sqlite3.Connection, pg_pool: asyncpg.Pool) -> Dict[int, int]:
    """
    Migrate papers table from SQLite to PostgreSQL.
    Returns mapping of old_id -> new_id
    """
    print("Migrating papers...")
    cursor = sqlite_conn.execute("SELECT * FROM papers ORDER BY id")
    papers = cursor.fetchall()
    
    id_mapping = {}
    
    # Get column names
    columns = [desc[0] for desc in cursor.description]
    
    async with pg_pool.acquire() as conn:
        for paper in papers:
            paper_dict = dict(zip(columns, paper))
            old_id = paper_dict['id']
            
            # Insert paper (id will be auto-generated)
            new_id = await conn.fetchval(
                """
                INSERT INTO papers (title, source_url, pdf_path, rag_status, rag_error, rag_updated_at, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                paper_dict.get('title'),
                paper_dict.get('source_url'),
                paper_dict['pdf_path'],
                paper_dict.get('rag_status'),
                paper_dict.get('rag_error'),
                paper_dict.get('rag_updated_at'),
                paper_dict.get('created_at')
            )
            
            id_mapping[old_id] = new_id
    
    print(f"  Migrated {len(papers)} papers")
    return id_mapping


async def migrate_sections_to_text_blocks(
    sqlite_conn: sqlite3.Connection,
    pg_pool: asyncpg.Pool,
    paper_id_mapping: Dict[int, int]
) -> None:
    """
    Migrate sections table to text_blocks table.
    Note: Sections don't have block_index, so we'll set it to 0.
    """
    print("Migrating sections to text_blocks...")
    cursor = sqlite_conn.execute("SELECT * FROM sections ORDER BY id")
    sections = cursor.fetchall()
    
    columns = [desc[0] for desc in cursor.description]
    
    batch = []
    migrated = 0
    
    for section in sections:
        section_dict = dict(zip(columns, section))
        old_paper_id = section_dict['paper_id']
        
        # Skip if paper wasn't migrated
        if old_paper_id not in paper_id_mapping:
            continue
        
        new_paper_id = paper_id_mapping[old_paper_id]
        
        batch.append((
            new_paper_id,
            section_dict['page_no'],
            0,  # block_index = 0 for legacy sections
            section_dict.get('text', ''),
            None,  # embedding will be generated during re-indexing
            None,  # bbox
            None,  # metadata
        ))
        
        if len(batch) >= BATCH_SIZE:
            async with pg_pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO text_blocks (paper_id, page_no, block_index, text, embedding, bbox, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (paper_id, page_no, block_index) DO NOTHING
                    """,
                    batch
                )
            migrated += len(batch)
            print(f"  Migrated {migrated} sections...")
            batch = []
    
    # Insert remaining batch
    if batch:
        async with pg_pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO text_blocks (paper_id, page_no, block_index, text, embedding, bbox, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (paper_id, page_no, block_index) DO NOTHING
                """,
                batch
            )
        migrated += len(batch)
    
    print(f"  Migrated {migrated} sections to text_blocks")


async def migrate_notes(
    sqlite_conn: sqlite3.Connection,
    pg_pool: asyncpg.Pool,
    paper_id_mapping: Dict[int, int]
) -> None:
    """Migrate notes table."""
    print("Migrating notes...")
    cursor = sqlite_conn.execute("SELECT * FROM notes ORDER BY id")
    notes = cursor.fetchall()
    
    columns = [desc[0] for desc in cursor.description]
    
    batch = []
    migrated = 0
    
    for note in notes:
        note_dict = dict(zip(columns, note))
        old_paper_id = note_dict.get('paper_id')
        
        # Handle NULL paper_id
        new_paper_id = paper_id_mapping.get(old_paper_id) if old_paper_id else None
        
        batch.append((
            new_paper_id,
            note_dict['body'],
            note_dict.get('title'),
            note_dict.get('tags_json'),
            note_dict.get('created_at')
        ))
        
        if len(batch) >= BATCH_SIZE:
            async with pg_pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO notes (paper_id, body, title, tags_json, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    batch
                )
            migrated += len(batch)
            print(f"  Migrated {migrated} notes...")
            batch = []
    
    if batch:
        async with pg_pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO notes (paper_id, body, title, tags_json, created_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                batch
            )
        migrated += len(batch)
    
    print(f"  Migrated {migrated} notes")


async def migrate_summaries(
    sqlite_conn: sqlite3.Connection,
    pg_pool: asyncpg.Pool,
    paper_id_mapping: Dict[int, int]
) -> None:
    """Migrate summaries table."""
    print("Migrating summaries...")
    cursor = sqlite_conn.execute("SELECT * FROM summaries ORDER BY id")
    summaries = cursor.fetchall()
    
    columns = [desc[0] for desc in cursor.description]
    
    batch = []
    migrated = 0
    
    for summary in summaries:
        summary_dict = dict(zip(columns, summary))
        old_paper_id = summary_dict['paper_id']
        
        if old_paper_id not in paper_id_mapping:
            continue
        
        new_paper_id = paper_id_mapping[old_paper_id]
        
        batch.append((
            new_paper_id,
            summary_dict.get('title'),
            summary_dict['content'],
            summary_dict.get('agent'),
            summary_dict.get('style'),
            summary_dict.get('word_count'),
            summary_dict.get('is_edited', 0),
            summary_dict.get('metadata_json'),
            summary_dict.get('created_at'),
            summary_dict.get('updated_at')
        ))
        
        if len(batch) >= BATCH_SIZE:
            async with pg_pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO summaries (paper_id, title, content, agent, style, word_count, 
                                          is_edited, metadata_json, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    batch
                )
            migrated += len(batch)
            print(f"  Migrated {migrated} summaries...")
            batch = []
    
    if batch:
        async with pg_pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO summaries (paper_id, title, content, agent, style, word_count, 
                                      is_edited, metadata_json, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                batch
            )
        migrated += len(batch)
    
    print(f"  Migrated {migrated} summaries")


async def migrate_question_sets_and_questions(
    sqlite_conn: sqlite3.Connection,
    pg_pool: asyncpg.Pool
) -> None:
    """Migrate question_sets and questions tables."""
    print("Migrating question sets...")
    
    # First migrate question_sets
    cursor = sqlite_conn.execute("SELECT * FROM question_sets ORDER BY id")
    question_sets = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    
    set_id_mapping = {}
    
    async with pg_pool.acquire() as conn:
        for qset in question_sets:
            qset_dict = dict(zip(columns, qset))
            old_id = qset_dict['id']
            
            new_id = await conn.fetchval(
                """
                INSERT INTO question_sets (prompt, created_at)
                VALUES ($1, $2)
                RETURNING id
                """,
                qset_dict['prompt'],
                qset_dict.get('created_at')
            )
            
            set_id_mapping[old_id] = new_id
    
    print(f"  Migrated {len(question_sets)} question sets")
    
    # Now migrate questions
    print("Migrating questions...")
    cursor = sqlite_conn.execute("SELECT * FROM questions ORDER BY id")
    questions = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    
    batch = []
    migrated = 0
    
    for question in questions:
        q_dict = dict(zip(columns, question))
        old_set_id = q_dict['set_id']
        
        if old_set_id not in set_id_mapping:
            continue
        
        new_set_id = set_id_mapping[old_set_id]
        
        batch.append((
            new_set_id,
            q_dict['kind'],
            q_dict['text'],
            q_dict.get('options_json'),
            q_dict.get('answer'),
            q_dict.get('explanation'),
            q_dict.get('reference')
        ))
        
        if len(batch) >= BATCH_SIZE:
            async with pg_pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO questions (set_id, kind, text, options_json, answer, explanation, reference)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    batch
                )
            migrated += len(batch)
            print(f"  Migrated {migrated} questions...")
            batch = []
    
    if batch:
        async with pg_pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO questions (set_id, kind, text, options_json, answer, explanation, reference)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                batch
            )
        migrated += len(batch)
    
    print(f"  Migrated {migrated} questions")


async def migrate_rag_qna(
    sqlite_conn: sqlite3.Connection,
    pg_pool: asyncpg.Pool,
    paper_id_mapping: Dict[int, int]
) -> None:
    """Migrate rag_qna table if it exists."""
    try:
        cursor = sqlite_conn.execute("SELECT * FROM rag_qna ORDER BY id")
        qna_records = cursor.fetchall()
        
        if not qna_records:
            print("No rag_qna records to migrate")
            return
        
        print("Migrating rag_qna records...")
        columns = [desc[0] for desc in cursor.description]
        
        batch = []
        migrated = 0
        
        for qna in qna_records:
            qna_dict = dict(zip(columns, qna))
            old_paper_id = qna_dict['paper_id']
            
            if old_paper_id not in paper_id_mapping:
                continue
            
            new_paper_id = paper_id_mapping[old_paper_id]
            
            batch.append((
                new_paper_id,
                qna_dict['question'],
                qna_dict['answer'],
                qna_dict.get('sources_json'),
                qna_dict.get('scope'),
                qna_dict.get('provider'),
                qna_dict.get('created_at')
            ))
            
            if len(batch) >= BATCH_SIZE:
                async with pg_pool.acquire() as conn:
                    await conn.executemany(
                        """
                        INSERT INTO rag_qna (paper_id, question, answer, sources_json, scope, provider, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        batch
                    )
                migrated += len(batch)
                print(f"  Migrated {migrated} rag_qna records...")
                batch = []
        
        if batch:
            async with pg_pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO rag_qna (paper_id, question, answer, sources_json, scope, provider, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    batch
                )
            migrated += len(batch)
        
        print(f"  Migrated {migrated} rag_qna records")
    except sqlite3.OperationalError:
        print("No rag_qna table found in SQLite, skipping")


async def validate_migration(sqlite_conn: sqlite3.Connection, pg_pool: asyncpg.Pool) -> bool:
    """Validate that migration was successful by comparing counts."""
    print("\nValidating migration...")
    
    tables = ['papers', 'notes', 'summaries', 'question_sets', 'questions']
    
    all_valid = True
    
    for table in tables:
        # Get SQLite count
        sqlite_count = sqlite_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        
        # Get PostgreSQL count
        async with pg_pool.acquire() as conn:
            pg_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
        
        match = "✓" if sqlite_count == pg_count else "✗"
        print(f"  {table}: SQLite={sqlite_count}, PostgreSQL={pg_count} {match}")
        
        if sqlite_count != pg_count:
            all_valid = False
    
    # Special check for sections -> text_blocks
    sections_count = sqlite_conn.execute("SELECT COUNT(*) FROM sections").fetchone()[0]
    async with pg_pool.acquire() as conn:
        text_blocks_count = await conn.fetchval("SELECT COUNT(*) FROM text_blocks")
    
    match = "✓" if sections_count == text_blocks_count else "✗"
    print(f"  sections -> text_blocks: SQLite={sections_count}, PostgreSQL={text_blocks_count} {match}")
    
    if sections_count != text_blocks_count:
        all_valid = False
    
    return all_valid


async def main():
    """Main migration process."""
    print("=" * 60)
    print("SQLite to PostgreSQL Migration")
    print("=" * 60)
    
    # Check if SQLite DB exists
    if not DB_PATH.exists():
        print(f"Error: SQLite database not found at {DB_PATH}")
        print("Nothing to migrate.")
        return
    
    print(f"Source: SQLite at {DB_PATH}")
    print(f"Target: PostgreSQL at {DATABASE_URL}")
    
    # Connect to SQLite
    sqlite_conn = sqlite3.connect(DB_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    
    # Connect to PostgreSQL and initialize schema
    print("\nInitializing PostgreSQL schema...")
    pg_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
    await init_db()
    print("✓ Schema initialized")
    
    try:
        # Migrate data
        print("\nStarting data migration...")
        
        # 1. Migrate papers (get ID mapping)
        paper_id_mapping = await migrate_papers(sqlite_conn, pg_pool)
        
        # 2. Migrate sections to text_blocks
        await migrate_sections_to_text_blocks(sqlite_conn, pg_pool, paper_id_mapping)
        
        # 3. Migrate notes
        await migrate_notes(sqlite_conn, pg_pool, paper_id_mapping)
        
        # 4. Migrate summaries
        await migrate_summaries(sqlite_conn, pg_pool, paper_id_mapping)
        
        # 5. Migrate question sets and questions
        await migrate_question_sets_and_questions(sqlite_conn, pg_pool)
        
        # 6. Migrate rag_qna (if exists)
        await migrate_rag_qna(sqlite_conn, pg_pool, paper_id_mapping)
        
        # Validate migration
        is_valid = await validate_migration(sqlite_conn, pg_pool)
        
        if is_valid:
            print("\n" + "=" * 60)
            print("✓ Migration completed successfully!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Update your .env file with DATABASE_URL")
            print("2. Run re-indexing to generate embeddings for text_blocks")
            print("3. Test the application with PostgreSQL")
        else:
            print("\n" + "=" * 60)
            print("⚠ Migration completed with warnings")
            print("=" * 60)
            print("Some counts don't match. Please review the migration.")
    
    finally:
        sqlite_conn.close()
        await pg_pool.close()


if __name__ == "__main__":
    asyncio.run(main())
