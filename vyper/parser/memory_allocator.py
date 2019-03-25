from typing import (
    Tuple,
)

from vyper.exceptions import (
    CompilerPanic,
)
from vyper.utils import (
    MemoryPositions,
)

from vyper.parser.lll_node import (
    LLLnode
)


class MemoryAllocator:
    next_mem: int

    def __init__(self, start_position: int = MemoryPositions.RESERVED_MEMORY):
        self.next_mem = start_position
        self.start_position = start_position

    # Get the next unused memory location
    def get_next_memory_position(self) -> int:
        return self.next_mem

    # Get effective memory position, from variable position.
    def get_var_position(self, pos: int):
        return self.start_position + pos

    # Grow memory by x bytes
    def increase_memory(self, size: int) -> Tuple[int, int]:
        if size % 32 != 0:
            raise CompilerPanic(
                'Memory misaligment, only multiples of 32 supported.'
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
        return LLLnode.from_list(
            [
                'add', x - self.memory_allocator.start_position, self.memory_offset_node
            ],
            annotation=f'mem_offset:{x}'
        )

    def increase_memory(self, size: int):
        before, after = self.memory_allocator.increase_memory(size)
        return (
            self._add_offset(before),
            self._add_offset(after)
        )

    def get_next_memory_position(self) -> LLLnode:
        o = self._add_offset(self.memory_allocator.get_next_memory_position())
        return o

    # Get effective memory position, from variable position.
    def get_var_position(self, pos: int):
        return LLLnode.from_list(
            [
                'add', self.memory_offset_node, pos
            ],
            annotation=f'var_offset:{pos}'
        )

    def get_size(self):
        return self.memory_allocator.get_size()
