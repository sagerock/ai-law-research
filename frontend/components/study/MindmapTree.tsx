'use client'

import { useState } from 'react'
import { ChevronRight, ChevronDown, Play } from 'lucide-react'
import type { MindmapNode } from '@/types'

interface MindmapTreeProps {
  nodes: MindmapNode[]
  currentNodeId: string | null
  onNodeClick: (nodeId: string) => void
  onStartBranch?: (nodeId: string) => void
}

interface TreeNode {
  node: MindmapNode
  children: TreeNode[]
}

function buildTree(nodes: MindmapNode[]): TreeNode[] {
  const map = new Map<string, TreeNode>()
  const roots: TreeNode[] = []

  for (const n of nodes) {
    map.set(n.node_id, { node: n, children: [] })
  }

  for (const n of nodes) {
    const treeNode = map.get(n.node_id)!
    if (n.parent_node_id && map.has(n.parent_node_id)) {
      map.get(n.parent_node_id)!.children.push(treeNode)
    } else {
      roots.push(treeNode)
    }
  }

  return roots
}

function masteryIcon(mastery: string) {
  switch (mastery) {
    case 'mastered': return '✅'
    case 'learning': return '🔄'
    default: return '○'
  }
}

function TreeNodeItem({
  treeNode,
  currentNodeId,
  onNodeClick,
  onStartBranch,
  depth,
}: {
  treeNode: TreeNode
  currentNodeId: string | null
  onNodeClick: (nodeId: string) => void
  onStartBranch?: (nodeId: string) => void
  depth: number
}) {
  const [expanded, setExpanded] = useState(depth < 2)
  const [hovering, setHovering] = useState(false)
  const { node, children } = treeNode
  const isCurrent = node.node_id === currentNodeId
  const hasChildren = children.length > 0

  const label = node.text.length > 40 ? node.text.slice(0, 37) + '...' : node.text

  return (
    <div>
      <div
        className={`group flex items-center gap-1 py-1 px-2 rounded cursor-pointer text-sm hover:bg-sage-50 transition-colors ${
          isCurrent ? 'bg-sage-100 font-semibold text-sage-800' : 'text-stone-600'
        }`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
        onMouseEnter={() => setHovering(true)}
        onMouseLeave={() => setHovering(false)}
        onClick={() => {
          if (hasChildren) setExpanded(!expanded)
          onNodeClick(node.node_id)
        }}
      >
        {hasChildren ? (
          expanded ? (
            <ChevronDown className="w-3 h-3 shrink-0" />
          ) : (
            <ChevronRight className="w-3 h-3 shrink-0" />
          )
        ) : (
          <span className="w-3" />
        )}
        <span className="shrink-0 text-xs">{masteryIcon(node.mastery)}</span>
        <span className="truncate flex-1">{label}</span>
        {hasChildren && hovering && onStartBranch && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onStartBranch(node.node_id)
            }}
            className="shrink-0 flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-sage-600 text-white text-xs hover:bg-sage-700 transition-colors"
            title="Study this branch"
          >
            <Play className="w-2.5 h-2.5" /> Focus
          </button>
        )}
      </div>
      {expanded && hasChildren && (
        <div>
          {children.map((child) => (
            <TreeNodeItem
              key={child.node.node_id}
              treeNode={child}
              currentNodeId={currentNodeId}
              onNodeClick={onNodeClick}
              onStartBranch={onStartBranch}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function MindmapTree({ nodes, currentNodeId, onNodeClick, onStartBranch }: MindmapTreeProps) {
  const tree = buildTree(nodes)

  return (
    <div className="overflow-y-auto max-h-full text-sm">
      <div className="font-semibold text-stone-700 px-2 py-1 text-xs uppercase tracking-wide mb-1">Topics</div>
      {tree.map((root) => (
        <TreeNodeItem
          key={root.node.node_id}
          treeNode={root}
          currentNodeId={currentNodeId}
          onNodeClick={onNodeClick}
          onStartBranch={onStartBranch}
          depth={0}
        />
      ))}
    </div>
  )
}
