import React, { useState, useMemo } from 'react';
import { Paper } from '@/shared/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { FileText, Trash2, Eye, Sparkles, Search, X, Filter } from 'lucide-react';

interface EnhancedPaperListProps {
  papers: Paper[];
  onSelect: (paper: Paper) => void;
  onDelete: (id: string) => void;
  onSummarize: (id: string) => void;
  selectedId?: string;
  selectedIds?: Set<string>;
  onSelectionChange?: (selectedIds: Set<string>) => void;
}

export function EnhancedPaperList({ 
  papers, 
  onSelect, 
  onDelete, 
  onSummarize, 
  selectedId,
  selectedIds = new Set(),
  onSelectionChange
}: EnhancedPaperListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [yearFilter, setYearFilter] = useState<string>('all');
  const [authorFilter, setAuthorFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'recent' | 'title' | 'cited'>('recent');

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
  const filteredPapers = useMemo(() => {
    let filtered = papers.filter(paper => {
      const matchesSearch = !searchQuery || 
        paper.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        paper.authors?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        paper.keywords?.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesYear = yearFilter === 'all' || paper.year === yearFilter;
      const matchesAuthor = authorFilter === 'all' || 
        paper.authors?.split(',').some(a => a.trim() === authorFilter);
      
      return matchesSearch && matchesYear && matchesAuthor;
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
  }, [papers, searchQuery, yearFilter, authorFilter, sortBy]);

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
                  <div className="h-10 w-10 rounded bg-secondary flex items-center justify-center shrink-0">
                    <FileText className="h-5 w-5 text-muted-foreground" />
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
                    <p className="text-xs text-muted-foreground mt-1">
                      {meta || 'Metadata pending'}
                    </p>
                  </div>
                </div>

                <div className="flex justify-end items-center gap-1 mt-3 pt-3 border-t border-border/50">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs"
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
                    className="h-7 text-xs text-blue-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSummarize(paper.id);
                    }}
                  >
                    <Sparkles className="h-3 w-3 mr-1" /> Summarize
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
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
