from typing import (
    Tuple,
)

from vyper.utils import (
    MemoryPositions,
)

from vyper.parser.lll_node import (
    LLLnode
)


class MemoryAlignmentException(Exception):
    pass


class MemoryAllocator:
    next_mem: int

    def __init__(self, start_position: int = MemoryPositions.RESERVED_MEMORY):
        self.next_mem = start_position
        self.start_position = start_position

    # Get the next unused memory location
    def get_next_memory_position(self) -> int:
        return self.next_mem

    # Grow memory by x bytes
    def increase_memory(self, size: int) -> Tuple[int, int]:
        if size % 32 != 0:
            raise MemoryAlignmentException(
                'Memory misaligment, only multiples of 32 supported.'
                'Please create an issue.'
            )
        before_value = self.next_mem
        self.next_mem += size
        return before_value, self.next_mem

    def get_size(self):
        return self.get_next_memory_position()


class PrivateMemoryAllocator:
    memory_offset_node: LLLnode
    memory_allocator: MemoryAllocator

    def __init__(self, memory_offset_node):
        self.memory_allocator = MemoryAllocator()
        self.memory_offset_node = memory_offset_node
        self.start_position = memory_offset_node

    def _add_offset(self, x):
        return LLLnode.from_list([
            'add', self.memory_offset_node, x - MemoryPositions.RESERVED_MEMORY
        ])

    def increase_memory(self, size: int):
        before, after = self.memory_allocator.increase_memory(size)
        return (
            self._add_offset(before),
            self._add_offset(after)
        )

    def get_next_memory_position(self) -> LLLnode:
        o = self._add_offset(self.memory_allocator.get_next_memory_position())
        return o

    def get_size(self):
        return self.memory_allocator.get_size()
