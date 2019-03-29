from vyper.parser.lll_node import (
    LLLnode,
)


def get_sig_statements(sig, pos):
    method_id_node = LLLnode.from_list(sig.method_id, pos=pos, annotation='%s' % sig.sig)

    if sig.private:
        sig_compare = 0
        private_label = LLLnode.from_list(
            ['label', 'priv_{}'.format(sig.method_id)],
            pos=pos, annotation='%s' % sig.sig
        )
    else:
        sig_compare = ['eq', ['mload', 0], method_id_node]
        private_label = ['pass']

    return sig_compare, private_label


def make_unpacker(ident, i_placeholder, begin_pos):
    start_label = 'dyn_unpack_start_' + ident
    end_label = 'dyn_unpack_end_' + ident
    return [
        'seq_unchecked',
        ['mstore', begin_pos, 'pass'],  # get len
        ['mstore', i_placeholder, 0],
        ['label', start_label],
        [  # break
            'if',
            ['ge', ['mload', i_placeholder], ['ceil32', ['mload', begin_pos]]],
            ['goto', end_label],
        ],
        [  # pop into correct memory slot.
            'mstore',
            ['add', ['add', begin_pos, 32], ['mload', i_placeholder]],
            'pass',
        ],
        ['mstore', i_placeholder, ['add', 32, ['mload', i_placeholder]]],  # increment i
        ['goto', start_label],
        ['label', end_label]]


def get_nonreentrant_lock(sig, global_ctx):
    nonreentrant_pre = [['pass']]
    nonreentrant_post = [['pass']]
    if sig.nonreentrant_key:
        nkey = global_ctx.get_nonrentrant_counter(sig.nonreentrant_key)
        nonreentrant_pre = [
            ['seq',
                ['assert', ['iszero', ['sload', nkey]]],
                ['sstore', nkey, 1]]]
        nonreentrant_post = [['sstore', nkey, 0]]
    return nonreentrant_pre, nonreentrant_post