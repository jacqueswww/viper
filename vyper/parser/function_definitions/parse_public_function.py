from vyper.exceptions import (
    FunctionDeclarationException,
)
from vyper.parser.arg_clamps import (
    make_arg_clamper,
)
from vyper.parser.context import (
    VariableRecord,
)
from vyper.parser.expr import (
    Expr,
)
from vyper.parser.function_definitions.utils import (
    get_nonreentrant_lock,
    get_sig_statements,
    make_unpacker,
)
from vyper.parser.lll_node import (
    LLLnode,
)
from vyper.parser.parser_utils import (
    getpos,
    make_setter,
)
from vyper.parser.stmt import (
    parse_body,
)
from vyper.signatures import (
    sig_utils,
)
from vyper.types.types import (
    BaseType,
    ByteArrayLike,
    get_size_of_type,
)
from vyper.utils import (
    MemoryPositions,
)


def get_public_arg_copier(sig, total_size, memory_dest, offset=4):
    # Copy arguments.
    copier = ['calldatacopy', memory_dest, offset, total_size]
    return copier


def validate_public_function(code, sig, global_ctx):
    # __init__ function may not have defaults.
    if sig.is_initializer() and sig.total_default_args > 0:
        raise FunctionDeclarationException(
            "__init__ function may not have default parameters.",
            code
        )

    # Check for duplicate variables with globals
    for arg in sig.args:
        if arg.name in global_ctx._globals:
            raise FunctionDeclarationException(
                "Variable name duplicated between "
                "function arguments and globals: " + arg.name,
                code
            )


def parse_public_function(code, sig, context):

    validate_public_function(code, sig, context.global_ctx)

    # Get nonreentrant lock
    nonreentrant_pre, nonreentrant_post = get_nonreentrant_lock(sig, context.global_ctx)

    # Allocate variable space.
    context.memory_allocator.increase_memory(sig.max_copy_size)

    clampers = []

    # Generate copiers
    if not len(sig.base_args):
        copier = 'pass'
    elif sig.name == '__init__':
        copier = ['codecopy', MemoryPositions.RESERVED_MEMORY, '~codelen', sig.base_copy_size]
    else:
        copier = get_public_arg_copier(
            sig=sig,
            total_size=sig.base_copy_size,
            memory_dest=MemoryPositions.RESERVED_MEMORY
        )
    clampers.append(copier)

    # Add asserts for payable and internal
    if not sig.payable:
        clampers.append(['assert', ['iszero', 'callvalue']])

    # Fill variable positions
    for i, arg in enumerate(sig.args):
        if i < len(sig.base_args):
            clampers.append(make_arg_clamper(
                arg.pos,
                context.memory_allocator.get_next_memory_position(),
                arg.typ,
                sig.name == '__init__',
            ))
        if isinstance(arg.typ, ByteArrayLike):
            mem_pos, _ = context.memory_allocator.increase_memory(32 * get_size_of_type(arg.typ))
            context.vars[arg.name] = VariableRecord(arg.name, mem_pos, arg.typ, False)
        else:
            context.vars[arg.name] = VariableRecord(
                arg.name,
                MemoryPositions.RESERVED_MEMORY + arg.pos,
                arg.typ,
                False,
            )

    # Create "clampers" (input well-formedness checkers)
    # Return function body
    if sig.name == '__init__':
        o = LLLnode.from_list(
            ['seq'] + clampers + [parse_body(code.body, context)],
            pos=getpos(code),
        )
    # Is default function.
    elif sig.is_default_func():
        if len(sig.args) > 0:
            raise FunctionDeclarationException(
                'Default function may not receive any arguments.', code
            )
        o = LLLnode.from_list(
            ['seq'] + clampers + [parse_body(code.body, context)],
            pos=getpos(code),
        )
    # Is a normal function.
    else:
        # Function with default parameters.
        if sig.total_default_args > 0:
            function_routine = "{}_{}".format(sig.name, sig.method_id)
            default_sigs = sig_utils.generate_default_arg_sigs(
                code, context.sigs, context.global_ctx
            )
            sig_chain = ['seq']

            for default_sig in default_sigs:
                sig_compare, private_label = get_sig_statements(default_sig, getpos(code))

                # Populate unset default variables
                populate_arg_count = len(sig.args) - len(default_sig.args)
                set_defaults = []
                if populate_arg_count > 0:
                    current_sig_arg_names = {x.name for x in default_sig.args}
                    missing_arg_names = [
                        arg.arg
                        for arg
                        in sig.default_args
                        if arg.arg not in current_sig_arg_names
                    ]
                    for arg_name in missing_arg_names:
                        value = Expr(sig.default_values[arg_name], context).lll_node
                        var = context.vars[arg_name]
                        left = LLLnode.from_list(var.pos, typ=var.typ, location='memory',
                                                 pos=getpos(code), mutable=var.mutable)
                        set_defaults.append(make_setter(left, value, 'memory', pos=getpos(code)))

                current_sig_arg_names = {x.name for x in default_sig.args}
                base_arg_names = {arg.name for arg in sig.base_args}
                copier_arg_count = len(default_sig.args) - len(sig.base_args)
                copier_arg_names = current_sig_arg_names - base_arg_names

                # Order copier_arg_names, this is very important.
                copier_arg_names = [x.name for x in default_sig.args if x.name in copier_arg_names]

                # Variables to be populated from calldata/stack.
                default_copiers = []
                if copier_arg_count > 0:
                    # Get map of variables in calldata, with thier offsets
                    offset = 4
                    calldata_offset_map = {}
                    for arg in default_sig.args:
                        calldata_offset_map[arg.name] = offset
                        offset += (
                            32
                            if isinstance(arg.typ, ByteArrayLike)
                            else get_size_of_type(arg.typ) * 32
                        )
                    # Copy set default parameters from calldata
                    dynamics = []
                    for arg_name in copier_arg_names:
                        var = context.vars[arg_name]
                        calldata_offset = calldata_offset_map[arg_name]

                        # Add clampers.
                        default_copiers.append(make_arg_clamper(
                            calldata_offset - 4,
                            var.pos,
                            var.typ,
                        ))
                        # Add copying code.
                        if isinstance(var.typ, ByteArrayLike):
                            _offset = ['add', 4, ['calldataload', calldata_offset]]
                        else:
                            _offset = calldata_offset
                        default_copiers.append(get_public_arg_copier(
                            sig=sig,
                            memory_dest=var.pos,
                            total_size=var.size * 32,
                            offset=_offset,
                        ))

                    # Unpack byte array if necessary.
                    if dynamics:
                        i_placeholder = context.new_placeholder(typ=BaseType('uint256'))
                        for idx, var_pos in enumerate(dynamics):
                            ident = 'unpack_default_sig_dyn_%d_arg%d' % (default_sig.method_id, idx)
                            default_copiers.append(make_unpacker(
                                ident=ident,
                                i_placeholder=i_placeholder,
                                begin_pos=var_pos,
                            ))
                    default_copiers.append(0)  # for over arching seq, POP

                sig_chain.append([
                    'if', sig_compare,
                    ['seq',
                        ['seq'] + set_defaults if set_defaults else ['pass'],
                        ['seq_unchecked'] + default_copiers if default_copiers else ['pass'],
                        ['goto', function_routine]]
                ])

            # Function with default parameters.
            o = LLLnode.from_list(
                [
                    'seq',
                    sig_chain,
                    [
                        'if', 0,  # can only be jumped into
                        [
                            'seq',
                            ['label', function_routine],
                            ['seq'] + nonreentrant_pre + clampers + [
                                parse_body(c, context)
                                for c in code.body
                            ] + nonreentrant_post + [['stop']]
                        ],
                    ],
                ], typ=None, pos=getpos(code))

        else:
            # Function without default parameters.
            sig_compare, _ = get_sig_statements(sig, getpos(code))
            o = LLLnode.from_list(
                [
                    'if',
                    sig_compare,
                    ['seq'] + nonreentrant_pre + clampers + [
                        parse_body(c, context)
                        for c
                        in code.body
                    ] + nonreentrant_post + [['stop']]
                ], typ=None, pos=getpos(code))
    return o