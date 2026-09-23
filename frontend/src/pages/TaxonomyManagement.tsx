import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import { 
  ClassificationNode, 
  getClassificationTreeFn, 
  createClassificationFn, 
  deactivateClassificationFn 
} from '../api/classifications';

export default function TaxonomyManagement() {
  const [tree, setTree] = useState<ClassificationNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState<ClassificationNode | null>(null);
  
  // Forms
  const [newNodeName, setNewNodeName] = useState('');
  const [newNodeCode, setNewNodeCode] = useState('');

  const { token } = useAuthStore();

  const fetchTree = async () => {
    setLoading(true);
    try {
      const data = await getClassificationTreeFn();
      setTree(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTree();
  }, [token]);

  const handleCreate = async () => {
    if (!newNodeCode || !newNodeName) return;
    try {
      await createClassificationFn({
        code: newNodeCode,
        name: newNodeName,
        parent_id: selectedNode ? selectedNode.classification_id : null
      });
      setNewNodeCode('');
      setNewNodeName('');
      fetchTree();
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeactivate = async () => {
    if (!selectedNode) return;
    try {
      await deactivateClassificationFn(selectedNode.classification_id);
      setSelectedNode(null);
      fetchTree();
    } catch (e) {
      console.error(e);
    }
  };

  const renderTree = (nodes: ClassificationNode[]) => {
    return (
      <ul className="pl-4 border-l border-gray-700 mt-2 space-y-2">
        {nodes.map(node => (
          <li key={node.classification_id} className="pt-2">
            <div 
              className={`cursor-pointer px-3 py-2 rounded-md transition-colors ${selectedNode?.classification_id === node.classification_id ? 'bg-primary-600 text-white' : 'hover:bg-gray-800 text-gray-300'}`}
              onClick={() => setSelectedNode(node)}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold">{node.code}</span>
                {node.status === 'INACTIVE' && <span className="text-xs bg-red-900 text-red-200 px-2 rounded-full">Inactive</span>}
              </div>
              <div className="text-sm opacity-80">{node.name}</div>
            </div>
            {node.children && node.children.length > 0 && renderTree(node.children)}
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div className="flex h-screen bg-gray-950 p-6 space-x-6 text-gray-100">
      
      {/* LEFT: Tree View */}
      <div className="w-1/2 bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-2xl overflow-y-auto">
        <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary-400 to-primary-600 mb-6">Taxonomy Hierarchy</h2>
        {loading ? (
          <div className="text-gray-500 animate-pulse">Loading Taxonomy...</div>
        ) : (
          <div>
            <div 
              className={`cursor-pointer px-3 py-2 rounded-md mb-4 border border-dashed ${!selectedNode ? 'bg-primary-900/30 border-primary-500 text-primary-300' : 'border-gray-700 text-gray-400'}`}
              onClick={() => setSelectedNode(null)}
            >
              Root Level (Deselect Node)
            </div>
            {renderTree(tree)}
          </div>
        )}
      </div>

      {/* RIGHT: Management Panel */}
      <div className="w-1/2 flex flex-col space-y-6">
        
        {/* Creation Panel */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-2xl">
          <h3 className="text-lg font-semibold text-gray-200 mb-4">
            {selectedNode ? `Create Child under ${selectedNode.code}` : "Create Root Classification"}
          </h3>
          <div className="space-y-4">
            <input 
              type="text" 
              placeholder="Code (e.g. VALVES_01)" 
              value={newNodeCode}
              onChange={e => setNewNodeCode(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500"
            />
            <input 
              type="text" 
              placeholder="Name (e.g. Gate Valves)" 
              value={newNodeName}
              onChange={e => setNewNodeName(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500"
            />
            <button 
              onClick={handleCreate}
              disabled={!newNodeCode || !newNodeName}
              className="w-full bg-gradient-to-r from-primary-600 to-primary-500 hover:from-primary-500 hover:to-primary-400 text-white font-medium py-2 rounded-lg transition-all shadow-[0_0_15px_rgba(37,99,235,0.3)] disabled:opacity-50"
            >
              Create Node
            </button>
          </div>
        </div>

        {/* Selected Node Details */}
        {selectedNode && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-2xl">
            <h3 className="text-lg font-semibold text-gray-200 mb-4">Node Details</h3>
            <div className="space-y-3 text-sm text-gray-400">
              <p><span className="text-gray-500 w-24 inline-block">ID:</span> <span className="font-mono bg-gray-950 px-2 py-1 rounded">{selectedNode.classification_id}</span></p>
              <p><span className="text-gray-500 w-24 inline-block">Code:</span> <span className="text-gray-200 font-semibold">{selectedNode.code}</span></p>
              <p><span className="text-gray-500 w-24 inline-block">Name:</span> <span className="text-gray-200">{selectedNode.name}</span></p>
              <p><span className="text-gray-500 w-24 inline-block">Level:</span> <span className="text-gray-200">{selectedNode.level}</span></p>
              <p><span className="text-gray-500 w-24 inline-block">Version:</span> <span className="text-gray-200">v{selectedNode.version}</span></p>
              <p><span className="text-gray-500 w-24 inline-block">Status:</span> 
                <span className={`px-2 py-0.5 rounded-full text-xs ml-2 ${selectedNode.status === 'ACTIVE' ? 'bg-green-900/50 text-green-400 border border-green-800' : 'bg-red-900/50 text-red-400 border border-red-800'}`}>
                  {selectedNode.status}
                </span>
              </p>
            </div>
            
            <div className="mt-8 pt-6 border-t border-gray-800">
              <h4 className="text-sm font-medium text-red-400 mb-4">Danger Zone</h4>
              <button 
                onClick={handleDeactivate}
                className="w-full bg-red-950 hover:bg-red-900 text-red-300 font-medium py-2 rounded-lg border border-red-900 transition-colors"
              >
                Deactivate Classification
              </button>
              <p className="text-xs text-gray-500 mt-3 text-center">Deactivating preserves historical tracebility for audit logs.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
