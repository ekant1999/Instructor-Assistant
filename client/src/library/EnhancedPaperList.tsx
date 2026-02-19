import React, { useState, useMemo } from 'react';
import { Paper } from '@/shared/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { FileType2, Globe, Trash2, Eye, Sparkles, Search, X, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

interface EnhancedPaperListProps {
  papers: Paper[];
  onSelect: (paper: Paper) => void;
  onDelete: (id: string) => void;
  onSummarize: (id: string) => void;
  onInfo?: (paper: Paper) => void;
  selectedId?: string;
  selectedIds?: Set<string>;
  onSelectionChange?: (selectedIds: Set<string>) => void;
  onSearchChange?: (query: string) => void;
}

export function EnhancedPaperList({ 
  papers, 
  onSelect, 
  onDelete, 
  onSummarize, 
  onInfo,
  selectedId,
  selectedIds = new Set(),
  onSelectionChange,
  onSearchChange
}: EnhancedPaperListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [yearFilter, setYearFilter] = useState<string>('all');
  const [authorFilter, setAuthorFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'recent' | 'title' | 'cited'>('recent');
  
  // Notify parent when search query changes
  React.useEffect(() => {
    if (onSearchChange) {
      const timer = setTimeout(() => {
        onSearchChange(searchQuery);
      }, 300); // Debounce
      return () => clearTimeout(timer);
    }
  }, [searchQuery, onSearchChange]);

  // Extract unique years and authors
  const years = useMemo(() => {
    const yearSet = new Set(papers.map(p => p.year).filter(Boolean));
    return Array.from(yearSet).sort((a, b) => b.localeCompare(a));
  }, [papers]);

  const authors = useMemo(() => {
    const authorSet = new Set<string>();
    papers.forEach(p => {
      if (p.authors) {
        p.authors.split(',').forEach(a => authorSet.add(a.trim()));
      }
    });
    return Array.from(authorSet).sort();
  }, [papers]);

  // Filter and sort papers
  // Note: Search is now handled by backend API via onSearchChange
  const filteredPapers = useMemo(() => {
    let filtered = papers.filter(paper => {
      const matchesYear = yearFilter === 'all' || paper.year === yearFilter;
      const matchesAuthor = authorFilter === 'all' || 
        paper.authors?.split(',').some(a => a.trim() === authorFilter);
      
      return matchesYear && matchesAuthor;
    });

    // Sort
    filtered.sort((a, b) => {
      if (sortBy === 'title') {
        return a.title.localeCompare(b.title);
      } else if (sortBy === 'cited') {
        // Mock citation count - in real app, this would come from metadata
        return 0;
      } else {
        // Recent - by updatedAt or createdAt
        const aTime = a.updatedAt || a.createdAt || 0;
        const bTime = b.updatedAt || b.createdAt || 0;
        return bTime - aTime;
      }
    });

    return filtered;
  }, [papers, yearFilter, authorFilter, sortBy]);

  const handleToggleSelect = (paperId: string) => {
    if (!onSelectionChange) return;
    const newSet = new Set(selectedIds);
    if (newSet.has(paperId)) {
      newSet.delete(paperId);
    } else {
      newSet.add(paperId);
    }
    onSelectionChange(newSet);
  };

  const handleSelectAll = () => {
    if (!onSelectionChange) return;
    if (selectedIds.size === filteredPapers.length) {
      onSelectionChange(new Set());
    } else {
      onSelectionChange(new Set(filteredPapers.map(p => p.id)));
    }
  };

  const clearFilters = () => {
    setSearchQuery('');
    setYearFilter('all');
    setAuthorFilter('all');
  };

  const hasActiveFilters = searchQuery || yearFilter !== 'all' || authorFilter !== 'all';

  return (
    <div className="flex flex-col h-full min-h-0 ia-paper-list">
      {/* Search and Filters */}
      <div className="p-4 border-b space-y-3 bg-background ia-paper-list-header">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search papers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 pr-9"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-2.5 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 gap-2">
          <Select value={yearFilter} onValueChange={setYearFilter}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="Year" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Years</SelectItem>
              {years.map(year => (
                <SelectItem key={year} value={year}>{year}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={authorFilter} onValueChange={setAuthorFilter}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="Author" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Authors</SelectItem>
              {authors.slice(0, 20).map(author => (
                <SelectItem key={author} value={author}>{author}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between gap-2">
          <Select value={sortBy} onValueChange={(v) => setSortBy(v as any)}>
            <SelectTrigger className="h-8 text-xs flex-1">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="recent">Recent</SelectItem>
              <SelectItem value="title">Title A-Z</SelectItem>
              <SelectItem value="cited">Most Cited</SelectItem>
            </SelectContent>
          </Select>

          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearFilters}
              className="h-8 text-xs"
            >
              <X className="h-3 w-3 mr-1" />
              Clear
            </Button>
          )}
        </div>

        {/* Multi-select controls */}
        {onSelectionChange && (
          <div className="flex items-center justify-between pt-2 border-t">
            <div className="flex items-center gap-2">
              <Checkbox
                checked={selectedIds.size === filteredPapers.length && filteredPapers.length > 0}
                onCheckedChange={handleSelectAll}
              />
              <span className="text-xs text-muted-foreground">
                {selectedIds.size > 0 ? `Selected: ${selectedIds.size} papers` : 'Select papers'}
              </span>
            </div>
            {selectedIds.size > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onSelectionChange(new Set())}
                className="h-7 text-xs"
              >
                Clear Selection
              </Button>
            )}
          </div>
        )}

        {/* Results count */}
        <div className="text-xs text-muted-foreground">
          {filteredPapers.length} {filteredPapers.length === 1 ? 'paper' : 'papers'}
          {searchQuery && ` matching "${searchQuery}"`}
        </div>
      </div>

      {/* Papers List */}
      <div className="flex-1 overflow-auto min-h-0 ia-paper-list-scroll">
        <div className="space-y-3 p-4 ia-paper-list-cards">
          {filteredPapers.map((paper) => {
            const isSelected = selectedIds.has(paper.id);
            const isActive = selectedId === paper.id;
            const meta = [paper.source, paper.year, paper.authors?.split(',')[0]].filter(Boolean).join(' • ');
            const statusLabel =
              paper.ragStatus === 'queued'
                ? 'Indexing queued'
                : paper.ragStatus === 'processing'
                  ? 'Indexing…'
                  : paper.ragStatus === 'done'
                    ? 'Indexed'
                    : paper.ragStatus === 'error'
                      ? 'Index error'
                      : null;
            const statusClasses =
              paper.ragStatus === 'queued'
                ? 'border-amber-500/40 text-amber-600'
                : paper.ragStatus === 'processing'
                  ? 'border-blue-500/40 text-blue-600'
                  : paper.ragStatus === 'done'
                    ? 'border-emerald-500/40 text-emerald-600'
                    : paper.ragStatus === 'error'
                      ? 'border-red-500/40 text-red-600'
                      : '';
            
            return (
              <Card
                key={paper.id}
                className={`p-4 cursor-pointer transition-all hover:shadow-md ia-paper-card ${
                  isActive ? 'border-primary ring-1 ring-primary' : 'hover:border-primary/50'
                } ${isSelected ? 'bg-primary/5' : ''}`}
                onClick={() => onSelect(paper)}
              >
                <div className="flex items-start gap-3">
                  {onSelectionChange && (
                    <Checkbox
                      checked={isSelected}
                      onCheckedChange={() => handleToggleSelect(paper.id)}
                      onClick={(e) => e.stopPropagation()}
                      className="mt-1"
                    />
                  )}
                  <div className="h-10 w-10 rounded bg-secondary flex items-center justify-center shrink-0 relative">
                    {paper.pdfUrl ? (
                      <FileType2 className="h-5 w-5 text-muted-foreground" />
                    ) : (
                      <Globe className="h-5 w-5 text-muted-foreground" />
                    )}
                    <span
                      className={cn(
                        "absolute -bottom-1 -right-1 rounded px-1 text-[9px] font-medium leading-3 border",
                        paper.pdfUrl
                          ? "bg-red-100 text-red-700 border-red-200 dark:bg-red-900/40 dark:text-red-200 dark:border-red-800/60"
                          : "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/40 dark:text-blue-200 dark:border-blue-800/60"
                      )}
                    >
                      {paper.pdfUrl ? "PDF" : "WEB"}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 
                      className="font-medium text-sm truncate" 
                      title={paper.title}
                      dangerouslySetInnerHTML={{
                        __html: searchQuery 
                          ? paper.title.replace(
                              new RegExp(`(${searchQuery})`, 'gi'),
                              '<mark class="bg-yellow-200 dark:bg-yellow-900">$1</mark>'
                            )
                          : paper.title
                      }}
                    />
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span>{meta || 'Metadata pending'}</span>
                      {statusLabel && (
                        <span
                          title={paper.ragError || statusLabel}
                          className={cn(
                            "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px]",
                            statusClasses
                          )}
                        >
                          <span className="h-1.5 w-1.5 rounded-full bg-current" />
                          {statusLabel}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t border-border/50 flex items-start gap-1">
                  <div className="flex-1 min-w-0 flex flex-wrap items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs px-2 shrink-0"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelect(paper);
                      }}
                    >
                      <Eye className="h-3 w-3 mr-1" /> Preview
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs px-2 shrink-0 text-blue-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSummarize(paper.id);
                      }}
                    >
                      <Sparkles className="h-3 w-3 mr-1" /> Summarize
                    </Button>
                    {onInfo && paper.pdfUrl && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs px-2 shrink-0"
                        onClick={(e) => {
                          e.stopPropagation();
                          onInfo(paper);
                        }}
                      >
                        <Info className="h-3 w-3 mr-1" /> Info
                      </Button>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 shrink-0 text-destructive hover:text-destructive hover:bg-destructive/10"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(paper.id);
                    }}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>

        {filteredPapers.length === 0 && (
          <div className="text-center py-10 text-muted-foreground text-sm border-2 border-dashed rounded-lg m-4">
            {hasActiveFilters ? 'No papers match your filters.' : 'No papers in library.'}
          </div>
        )}
      </div>
    </div>
  );
}
