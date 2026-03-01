'use client'

import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical } from 'lucide-react'
import { ReactNode } from 'react'

interface SortableCollectionItemProps {
  id: string
  children: ReactNode
}

export default function SortableCollectionItem({ id, children }: SortableCollectionItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div ref={setNodeRef} style={style} className="flex items-stretch gap-0">
      <button
        {...attributes}
        {...listeners}
        className="flex items-center px-1.5 text-stone-300 hover:text-stone-500 cursor-grab active:cursor-grabbing touch-none flex-shrink-0"
        aria-label="Drag to reorder"
      >
        <GripVertical className="h-4 w-4" />
      </button>
      <div className="flex-1 min-w-0">
        {children}
      </div>
    </div>
  )
}
