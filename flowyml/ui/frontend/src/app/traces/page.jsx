import React, { useState, useEffect } from 'react';
import { fetchApi } from '../../utils/api';
import { Activity, Zap, MessageSquare, Clock, DollarSign } from 'lucide-react';
import { useProject } from '../../contexts/ProjectContext';

export function Traces() {
  const [traces, setTraces] = useState([]);
  const [selectedTrace, setSelectedTrace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState('all');
  const { selectedProject } = useProject();

  useEffect(() => {
    fetchTraces();
  }, [filterType, selectedProject]);

  const fetchTraces = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterType !== 'all') {
        params.append('event_type', filterType);
      }
      if (selectedProject) {
        params.append('project', selectedProject);
      }

      const response = await fetchApi(`/api/traces?${params}`);
      const data = await response.json();
      setTraces(data);
    } catch (error) {
      console.error('Failed to fetch traces:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTraceDetails = async (traceId) => {
    try {
      const response = await fetchApi(`/api/traces/${traceId}`);
      const data = await response.json();
      setSelectedTrace(data);
    } catch (error) {
      console.error('Failed to fetch trace details:', error);
    }
  };

  const formatDuration = (duration) => {
    if (!duration) return 'N/A';
    return `${(duration * 1000).toFixed(0)}ms`;
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'success': return 'text-green-400';
      case 'error': return 'text-red-400';
      case 'running': return 'text-yellow-400';
      default: return 'text-gray-400';
    }
  };

  const getEventTypeIcon = (type) => {
    switch (type) {
      case 'llm': return <MessageSquare className="w-4 h-4" />;
      case 'tool': return <Zap className="w-4 h-4" />;
      default: return <Activity className="w-4 h-4" />;
    }
  };

  const TraceTree = ({ events, level = 0 }) => {
    if (!events) return null;

    return (
      <div className={`pl-${level * 4}`}>
        {events.map((event, idx) => (
          <div key={idx} className="mb-2">
            <div className="flex items-center gap-2 p-2 bg-gray-800/50 rounded border border-gray-700/50 hover:border-blue-500/50 transition-colors">
              <div className="flex items-center gap-2 flex-1">
                {getEventTypeIcon(event.event_type)}
                <span className="font-medium">{event.name}</span>
                <span className={`text-sm ${getStatusColor(event.status)}`}>
                  {event.status}
                </span>
              </div>

              <div className="flex items-center gap-4 text-sm text-gray-400">
                {event.duration && (
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatDuration(event.duration)}
                  </div>
                )}

                {event.total_tokens > 0 && (
                  <div className="flex items-center gap-1">
                    <Activity className="w-3 h-3" />
                    {event.total_tokens} tokens
                  </div>
                )}

                {event.cost > 0 && (
                  <div className="flex items-center gap-1">
                    <DollarSign className="w-3 h-3" />
                    ${event.cost.toFixed(4)}
                  </div>
                )}
              </div>
            </div>

            {event.children && event.children.length > 0 && (
              <div className="ml-6 mt-2 border-l-2 border-gray-700/50 pl-2">
                <TraceTree events={event.children} level={level + 1} />
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">🔍 LLM Traces</h1>

        <div className="flex gap-2">
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg"
          >
            <option value="all">All Types</option>
            <option value="llm">LLM Calls</option>
            <option value="tool">Tool Calls</option>
            <option value="chain">Chains</option>
            <option value="agent">Agents</option>
          </select>

          <button
            onClick={fetchTraces}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <p className="mt-4 text-gray-400">Loading traces...</p>
        </div>
      ) : traces.length === 0 ? (
        <div className="text-center py-12 bg-gray-800/30 rounded-lg border-2 border-dashed border-gray-700">
          <Activity className="w-12 h-12 mx-auto text-gray-600 mb-4" />
          <p className="text-gray-400">No traces found</p>
          <p className="text-sm text-gray-500 mt-2">
            Use @trace_llm decorator to track LLM calls
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {traces.map((trace) => {
            // Group by trace_id
            const traceId = trace.trace_id;

            return (
              <div
                key={trace.event_id}
                className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-4 hover:border-blue-500/50 transition-all cursor-pointer"
                onClick={() => fetchTraceDetails(traceId)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    {getEventTypeIcon(trace.event_type)}
                    <div>
                      <h3 className="font-semibold text-lg">{trace.name}</h3>
                      <p className="text-sm text-gray-400">
                        Trace ID: {traceId.slice(0, 8)}...
                      </p>
                    </div>
                  </div>

                  <span className={`px-3 py-1 rounded-full text-sm ${getStatusColor(trace.status)}`}>
                    {trace.status}
                  </span>
                </div>

                <div className="grid grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Duration:</span>
                    <span className="ml-2 text-gray-300">{formatDuration(trace.duration)}</span>
                  </div>

                  {trace.model && (
                    <div>
                      <span className="text-gray-500">Model:</span>
                      <span className="ml-2 text-gray-300">{trace.model}</span>
                    </div>
                  )}

                  {trace.total_tokens > 0 && (
                    <div>
                      <span className="text-gray-500">Tokens:</span>
                      <span className="ml-2 text-gray-300">
                        {trace.total_tokens} ({trace.prompt_tokens}/{trace.completion_tokens})
                      </span>
                    </div>
                  )}

                  {trace.cost > 0 && (
                    <div>
                      <span className="text-gray-500">Cost:</span>
                      <span className="ml-2 text-gray-300">${trace.cost.toFixed(4)}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Trace Details Modal */}
      {selectedTrace && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-6 z-50">
          <div className="bg-gray-900 rounded-lg max-w-4xl w-full max-h-[80vh] overflow-auto border border-gray-700">
            <div className="sticky top-0 bg-gray-900 border-b border-gray-700 p-4 flex justify-between items-center">
              <h2 className="text-xl font-bold">Trace Details</h2>
              <button
                onClick={() => setSelectedTrace(null)}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg"
              >
                Close
              </button>
            </div>

            <div className="p-6">
              <TraceTree events={selectedTrace} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
