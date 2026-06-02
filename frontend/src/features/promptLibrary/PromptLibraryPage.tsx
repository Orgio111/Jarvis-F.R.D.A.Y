import React, { useState } from 'react';
import { usePromptLibrary } from './usePromptLibrary';
import type { PromptTemplateView } from './usePromptLibrary';

export const PromptLibraryPage: React.FC = () => {
  const {
    templates,
    loading,
    error,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    applyTemplate,
    filterTemplates,
  } = usePromptLibrary();

  const [search, setSearch] = useState('');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [editing, setEditing] = useState<Partial<PromptTemplateView> | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [appliedText, setAppliedText] = useState<string | null>(null);

  const allTags = Array.from(new Set(templates.flatMap((t) => t.tags)));
  const filtered = filterTemplates(search, selectedTag ?? undefined);

  const handleSave = async () => {
    if (!editing) return;
    if (editing.id) {
      await updateTemplate(editing.id, editing);
    } else {
      await createTemplate({
        name: editing.name ?? 'Untitled',
        description: editing.description ?? '',
        template: editing.template ?? '',
        tags: editing.tags ?? [],
        variables: editing.variables ?? [],
      });
    }
    setEditing(null);
    setShowForm(false);
  };

  const handleApply = async (id: string) => {
    const result = await applyTemplate(id, {});
    if (result) setAppliedText(result);
  };

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Prompt Library</h1>
        <button
          onClick={() => { setEditing({}); setShowForm(true); }}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
        >
          + New Template
        </button>
      </div>

      {error && (
        <div className="bg-red-900/40 border border-red-500 rounded-lg p-3 text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Search + Tag filters */}
      <div className="flex gap-3 flex-wrap">
        <input
          type="text"
          placeholder="Search templates..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 min-w-48 bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-400 focus:outline-none focus:border-blue-500"
        />
        <button
          onClick={() => setSelectedTag(null)}
          className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
            !selectedTag ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          All
        </button>
        {allTags.map((tag) => (
          <button
            key={tag}
            onClick={() => setSelectedTag(selectedTag === tag ? null : tag)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              selectedTag === tag ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {tag}
          </button>
        ))}
      </div>

      {/* Applied preview */}
      {appliedText && (
        <div className="bg-green-900/30 border border-green-600 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-green-400 text-sm font-medium">Applied Template</span>
            <button onClick={() => setAppliedText(null)} className="text-gray-400 hover:text-white text-xs">
              Dismiss
            </button>
          </div>
          <pre className="text-gray-200 text-sm whitespace-pre-wrap font-mono">{appliedText}</pre>
          <button
            onClick={() => navigator.clipboard.writeText(appliedText)}
            className="mt-2 text-xs text-blue-400 hover:text-blue-300"
          >
            Copy to clipboard
          </button>
        </div>
      )}

      {/* Template grid */}
      {loading ? (
        <div className="text-gray-400 text-center py-12">Loading templates...</div>
      ) : filtered.length === 0 ? (
        <div className="text-gray-500 text-center py-12">No templates found.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map((tpl) => (
            <TemplateCard
              key={tpl.id}
              template={tpl}
              onEdit={() => { setEditing(tpl); setShowForm(true); }}
              onDelete={() => deleteTemplate(tpl.id)}
              onApply={() => handleApply(tpl.id)}
            />
          ))}
        </div>
      )}

      {/* Edit / Create form modal */}
      {showForm && editing !== null && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-lg space-y-4">
            <h2 className="text-white font-semibold text-lg">
              {editing.id ? 'Edit Template' : 'New Template'}
            </h2>

            <div className="space-y-3">
              <input
                type="text"
                placeholder="Template name"
                value={editing.name ?? ''}
                onChange={(e) => setEditing({ ...editing, name: e.target.value })}
                className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              />
              <input
                type="text"
                placeholder="Description (optional)"
                value={editing.description ?? ''}
                onChange={(e) => setEditing({ ...editing, description: e.target.value })}
                className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              />
              <textarea
                placeholder="Template text — use {{variable}} for placeholders"
                value={editing.template ?? ''}
                onChange={(e) => setEditing({ ...editing, template: e.target.value })}
                rows={6}
                className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-blue-500 resize-none"
              />
              <input
                type="text"
                placeholder="Tags (comma separated)"
                value={(editing.tags ?? []).join(', ')}
                onChange={(e) =>
                  setEditing({
                    ...editing,
                    tags: e.target.value.split(',').map((t) => t.trim()).filter(Boolean),
                  })
                }
                className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setEditing(null); setShowForm(false); }}
                className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

interface TemplateCardProps {
  template: PromptTemplateView;
  onEdit: () => void;
  onDelete: () => void;
  onApply: () => void;
}

const TemplateCard: React.FC<TemplateCardProps> = ({ template, onEdit, onDelete, onApply }) => (
  <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-4 space-y-3 hover:border-gray-500 transition-colors">
    <div className="flex items-start justify-between gap-2">
      <div>
        <h3 className="text-white font-medium text-sm">{template.name}</h3>
        {template.description && (
          <p className="text-gray-400 text-xs mt-0.5">{template.description}</p>
        )}
      </div>
      {template.is_builtin && (
        <span className="shrink-0 px-2 py-0.5 bg-purple-900/50 border border-purple-700 rounded text-purple-300 text-xs">
          Built-in
        </span>
      )}
    </div>

    <pre className="text-gray-300 text-xs font-mono bg-gray-900/60 rounded p-2 line-clamp-3 whitespace-pre-wrap overflow-hidden">
      {template.template}
    </pre>

    {template.tags.length > 0 && (
      <div className="flex flex-wrap gap-1">
        {template.tags.map((tag) => (
          <span key={tag} className="px-2 py-0.5 bg-gray-700 text-gray-300 rounded-full text-xs">
            {tag}
          </span>
        ))}
      </div>
    )}

    {template.variables.length > 0 && (
      <div className="text-xs text-gray-500">
        Variables: {template.variables.map((v) => `{{${v}}}`).join(', ')}
      </div>
    )}

    <div className="flex items-center gap-2 pt-1">
      <button
        onClick={onApply}
        className="flex-1 py-1.5 bg-blue-600/80 text-white rounded-lg hover:bg-blue-600 text-xs font-medium transition-colors"
      >
        Apply
      </button>
      {!template.is_builtin && (
        <>
          <button
            onClick={onEdit}
            className="px-3 py-1.5 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 text-xs transition-colors"
          >
            Edit
          </button>
          <button
            onClick={onDelete}
            className="px-3 py-1.5 bg-red-900/50 text-red-400 rounded-lg hover:bg-red-900 text-xs transition-colors"
          >
            Delete
          </button>
        </>
      )}
    </div>
  </div>
);
