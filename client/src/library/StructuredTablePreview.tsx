import React from 'react';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ApiPaperTableInfo } from '@/lib/api-types';

interface StructuredTablePreviewProps {
  table: ApiPaperTableInfo;
  className?: string;
}

interface TableGridProps {
  table: ApiPaperTableInfo;
  headers: string[];
  rows: string[][];
  showSyntheticRowNumbers: boolean;
  className?: string;
  expanded?: boolean;
}

function normalizeTablePreview(table: ApiPaperTableInfo): {
  headers: string[];
  rows: string[][];
} {
  const previewHeaders = Array.isArray(table.headers_preview) ? table.headers_preview : [];
  const previewRows = Array.isArray(table.rows_preview) ? table.rows_preview : [];
  const colCount = Math.max(
    table.n_cols || 0,
    previewHeaders.length,
    ...previewRows.map((row) => row.length),
  );
  const headers = Array.from({ length: colCount }, (_, idx) => {
    const value = previewHeaders[idx] || '';
    return value.trim() || `col_${idx + 1}`;
  });
  const rows = previewRows.map((row) => {
    if (row.length >= colCount) return row.slice(0, colCount);
    return [...row, ...Array(colCount - row.length).fill('')];
  });
  return { headers, rows };
}

function isIndexLikeHeader(value: string): boolean {
  const normalized = value.trim().toLowerCase();
  return normalized === '#' || normalized === 'no.' || normalized === 'no' || normalized === 'idx' || normalized === 'index';
}

function looksLikeSequentialIndex(rows: string[][]): boolean {
  if (rows.length === 0) return false;
  const sample = rows.slice(0, Math.min(rows.length, 6));
  return sample.every((row, idx) => {
    const firstCell = String(row[0] || '').trim();
    return firstCell === String(idx + 1);
  });
}

function StructuredTableGrid({
  table,
  headers,
  rows,
  showSyntheticRowNumbers,
  className,
  expanded = false,
}: TableGridProps) {
  const cellWidthClass = expanded ? 'min-w-[10rem] max-w-[32rem]' : 'min-w-[8rem] max-w-[20rem]';
  const textClassName = expanded ? 'text-xs leading-6' : 'text-[11px] leading-5';

  return (
    <div className={className}>
      <table className={`w-max min-w-full border-collapse table-auto ${textClassName}`}>
        <thead className="bg-muted/50 sticky top-0 z-10">
          <tr>
            {showSyntheticRowNumbers && (
              <th className="text-left align-top p-2 border-b border-r w-12 min-w-12 sticky left-0 bg-muted/50 z-20">
                #
              </th>
            )}
            {headers.map((header, idx) => (
              <th
                key={`table-${table.id}-header-${idx}`}
                className={`text-left align-top p-2 border-b border-r whitespace-pre-wrap break-words ${cellWidthClass}`}
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIdx) => (
            <tr
              key={`table-${table.id}-row-${rowIdx}`}
              className="odd:bg-background even:bg-muted/20"
            >
              {showSyntheticRowNumbers && (
                <td className="align-top p-2 border-b border-r text-muted-foreground sticky left-0 bg-inherit backdrop-blur-[1px]">
                  {rowIdx + 1}
                </td>
              )}
              {row.map((cell, cellIdx) => (
                <td
                  key={`table-${table.id}-row-${rowIdx}-cell-${cellIdx}`}
                  className={`align-top p-2 border-b border-r whitespace-pre-wrap break-words ${cellWidthClass}`}
                >
                  {cell || '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function StructuredTablePreview({ table, className }: StructuredTablePreviewProps) {
  const [expanded, setExpanded] = React.useState(false);
  const normalized = React.useMemo(() => normalizeTablePreview(table), [table]);
  const hasStructuredPreview = normalized.headers.length > 0 && normalized.rows.length > 0;

  if (!hasStructuredPreview) {
    if (!table.markdown_preview) {
      return (
        <div className="text-xs text-muted-foreground">
          Structured preview not available for this table.
        </div>
      );
    }

    return (
      <pre className={`text-[11px] leading-5 whitespace-pre-wrap break-words bg-background border rounded-md p-2 ${className || ''}`}>
        {table.markdown_preview}
      </pre>
    );
  }

  const showSyntheticRowNumbers = !(isIndexLikeHeader(normalized.headers[0] || '') || looksLikeSequentialIndex(normalized.rows));
  const previewSummary = `Showing ${normalized.rows.length} of ${table.n_rows} row${table.n_rows === 1 ? '' : 's'} and ${normalized.headers.length} column${normalized.headers.length === 1 ? '' : 's'}.`;

  return (
    <>
      <div className={`border rounded-md bg-background overflow-hidden ${className || ''}`}>
        <div className="flex flex-wrap items-center gap-2 px-3 py-2 border-b bg-muted/30 text-[11px] text-muted-foreground">
          <span>{previewSummary}</span>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-7 text-[11px]"
              onClick={() => setExpanded(true)}
            >
              Expand preview
            </Button>
          </div>
          <span className="hidden md:inline ml-auto">Scroll horizontally for full width</span>
        </div>
        <div className="max-h-72 overflow-auto">
          <StructuredTableGrid
            table={table}
            headers={normalized.headers}
            rows={normalized.rows}
            showSyntheticRowNumbers={showSyntheticRowNumbers}
          />
        </div>
        {table.preview_truncated && (
          <div className="px-3 py-2 text-[11px] text-muted-foreground border-t bg-muted/20">
            Showing first {normalized.rows.length} rows in preview.
          </div>
        )}
      </div>

      <Dialog open={expanded} onOpenChange={setExpanded}>
        <DialogContent className="w-[96vw] max-w-[96vw] h-[90vh] flex flex-col overflow-hidden">
          <DialogHeader>
            <DialogTitle>Expanded Table Preview</DialogTitle>
            <DialogDescription>
              Table {table.id} on page {table.page_no}. {previewSummary}
            </DialogDescription>
            {table.caption ? (
              <div className="text-sm text-muted-foreground leading-6">{table.caption}</div>
            ) : null}
          </DialogHeader>

          <div className="flex-1 min-h-0 border rounded-md overflow-auto bg-background">
            <StructuredTableGrid
              table={table}
              headers={normalized.headers}
              rows={normalized.rows}
              showSyntheticRowNumbers={showSyntheticRowNumbers}
              expanded
            />
          </div>

          {table.preview_truncated && (
            <div className="text-xs text-muted-foreground">
              This expanded view uses the stored preview rows, not the full underlying table.
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

export default StructuredTablePreview;
