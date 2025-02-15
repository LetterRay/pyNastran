from __future__ import annotations
from itertools import zip_longest
from collections import defaultdict
from typing import Any, TYPE_CHECKING
import numpy as np
#from pyNastran.bdf.field_writer_8 import print_card_8
from pyNastran.utils.numpy_utils import integer_types
from pyNastran.bdf.cards.base_card import expand_thru, _format_comment
from pyNastran.bdf.bdf_interface.assign_type import (
    integer, string, parse_components,
    integer_or_string, fields,
    #integer_or_blank, double_or_blank, # components_or_blank,
    integer_string_or_blank, parse_components_or_blank,
    components_or_blank as fcomponents_or_blank)

#from pyNastran.dev.bdf_vectorized3.bdf_interface.geom_check import geom_check
from pyNastran.dev.bdf_vectorized3.cards.base_card import (
    VectorizedBaseCard, parse_node_check, get_print_card_8_16,
    hslice_by_idim, make_idim)
from pyNastran.dev.bdf_vectorized3.cards.write_utils import (
    get_print_card, update_field_size, array_str, array_default_int)
from pyNastran.dev.bdf_vectorized3.bdf_interface.geom_check import geom_check


if TYPE_CHECKING:  # pragma: no cover
    from pyNastran.dev.bdf_vectorized3.bdf import BDF
    from pyNastran.dev.bdf_vectorized3.types import TextIOLike
    from pyNastran.bdf.bdf_interface.bdf_card import BDFCard


class ABCOQSET(VectorizedBaseCard):
    """
    Defines degrees-of-freedom in the analysis set (A-set).

    +-------+-----+-----+------+------+-----+-----+-----+-----+
    |  1    |  2  | 3   |  4   |  5   |  6  |  7  |  8  | 9   |
    +=======+=====+=====+======+======+=====+=====+=====+=====+
    | ASET  | ID1 | C1  | ID2  |  C2  | ID3 | C3  | ID4 | C4  |
    +-------+-----+-----+------+------+-----+-----+-----+-----+
    | ASET  | 16  |  2  |  23  | 3516 |  1  |  4  |     |     |
    +-------+-----+-----+------+------+-----+-----+-----+-----+

    +-------+-----+-----+------+------+-----+-----+-----+-----+
    |   1   |  2  |  3  |   4  |  5   |  6  |  7  |  8  |  9  |
    +=======+=====+=====+======+======+=====+=====+=====+=====+
    | ASET1 |  C  | ID1 |  ID2 | ID3  | ID4 | ID5 | ID6 | ID7 |
    +-------+-----+-----+------+------+-----+-----+-----+-----+
    |       | ID8 | ID9 |      |      |     |     |     |     |
    +-------+-----+-----+------+------+-----+-----+-----+-----+
    | ASET1 |  C  | ID1 | THRU | ID2  |     |     |     |     |
    +-------+-----+-----+------+------+-----+-----+-----+-----+
    """
    _id_name = 'node_id'
    def __init__(self, model: BDF):
        super().__init__(model)
        #self._is_sorted = False
        self.component = np.array([], dtype='int32')
        self.node_id = np.array([], dtype='int32')

    def add_set(self, nids: list[int], components: list[int],
                 comment: str='') -> int:
        assert isinstance(nids, (list, np.ndarray, tuple))
        assert isinstance(components, (list, np.ndarray, tuple))
        nnodes = len(nids)
        ncomp = len(components)
        assert nnodes == ncomp, (nnodes, ncomp)
        self.cards.append((nids, components, comment))
        #if comment:
            #self.comment[nid] = _format_comment(comment)
        self.n += nnodes
        return self.n

    def add_set1(self, nids: list[int], component: int,
                  comment: str='') -> int:
        assert isinstance(component, (str, integer_types)), component
        nids = expand_thru(nids, set_fields=True, sort_fields=False)
        nnodes = len(nids)
        components = [component] * nnodes
        self.cards.append((nids, components, comment))
        #if comment:
            #self.comment[nid] = _format_comment(comment)
        self.n += nnodes
        return self.n

    def add_card(self, card: BDFCard, comment: str=''):
        card_name = card[0].upper()
        #new_name0 = card_name[:-1] if card.endswith('1') else card_name
        msg = f'add_card(...) has been removed for {card_name}.  Use add_set_card or add_set1_card'
        raise AttributeError(msg)

    def add_set_card(self, card: BDFCard, comment: str='') -> int:
        if self.debug:
            self.model.log.debug(f'adding card {card}')

        ids = []
        components = []
        nterms = len(card) // 2
        for n in range(nterms):
            i = n * 2 + 1
            idi = integer(card, i, 'ID' + str(n))
            component = parse_components_or_blank(card, i + 1, 'component' + str(n))
            ids.append(idi)
            components.append(component)
        #return cls(ids, components, comment=comment)

        self.cards.append((ids, components, comment))
        #if comment:
            #self.comment[nid] = comment
        self.n += len(ids)
        return self.n

    def add_set1_card(self, card: BDFCard, comment: str='') -> int:
        if self.debug:
            self.model.log.debug(f'adding card {card}')

        components_str = fcomponents_or_blank(card, 1, 'components', '0')
        component = int(components_str)

        nfields = len(card)
        ids = []
        i = 1
        for ifield in range(2, nfields):
            idi = integer_string_or_blank(card, ifield, 'ID%i' % i)
            if idi:
                i += 1
                ids.append(idi)
        ids = expand_thru(ids, set_fields=True, sort_fields=True)
        components = [component] * len(ids)
        #return cls(ids, components, comment=comment)

        self.cards.append((ids, components, comment))
        #if comment:
            #self.comment[nid] = comment
        self.n += len(ids)
        return self.n

    @VectorizedBaseCard.parse_cards_check
    def parse_cards(self) -> None:
        idtype = self.model.idtype
        #ncards = len(self.cards)
        if self.debug:
            self.model.log.debug(f'parse {self.type}')


        node_id_list = []
        component_list = []
        #comment = {}
        for i, card in enumerate(self.cards):
            (nidi, componenti, commenti) = card
            assert isinstance(nidi, list), nidi
            assert isinstance(componenti, list), componenti
            node_id_list.extend(nidi)
            component_list.extend(componenti)
            #if commenti:
                #comment[i] = commenti
                #comment[nidi] = commenti

        node_id = np.array(node_id_list, dtype=idtype)
        component = np.array(component_list, dtype='int32')
        self._save(node_id, component)
        self.sort()
        self.cards = []

    def _save(self,
              node_id: np.ndarray,
              component: np.ndarray,
              comment: dict[int, str]=None) -> None:
        #ncards = len(node_id)
        ncards_existing = len(self.node_id)

        if ncards_existing != 0:
            node_id = np.hstack([self.node_id, node_id])
            component = np.hstack([self.component, component])
        #if comment:
            #self.comment.update(comment)
        self.node_id = node_id
        self.component = component
        self.n = len(node_id)
        #self.sort()
        #self.cards = []

    #def slice_by_node_id(self, node_id: np.ndarray) -> GRID:
        #inid = self._node_index(node_id)
        #return self.slice_card(inid)

    #def slice_card_by_node_id(self, node_id: np.ndarray) -> GRID:
        #"""uses a node_ids to extract GRIDs"""
        #inid = self.index(node_id)
        ##assert len(self.node_id) > 0, self.node_id
        ##i = np.searchsorted(self.node_id, node_id)
        #grid = self.slice_card_by_index(inid)
        #return grid

    #def slice_card_by_index(self, i: np.ndarray) -> GRID:
        #"""uses a node_index to extract GRIDs"""
        #assert self.xyz.shape == self._xyz_cid0.shape
        #assert len(self.node_id) > 0, self.node_id
        #i = np.atleast_1d(np.asarray(i, dtype=self.node_id.dtype))
        #i.sort()
        #grid = GRID(self.model)
        #self.__apply_slice__(grid, i)
        #return grid

    def __apply_slice__(self, grid: ASET, i: np.ndarray) -> None:
        self._slice_comment(grid, i)
        grid.n = len(i)
        grid.node_id = self.node_id[i]
        grid.component = self.component[i]

    def geom_check(self, missing: dict[str, np.ndarray]):
        nid = self.model.grid.node_id
        geom_check(self,
                   missing,
                   node=(nid, self.node_id),)

    @parse_node_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        max_int = self.node_id.max()
        size = update_field_size(max_int, size)
        print_card = get_print_card(size, max_int)

        comp_to_nids = defaultdict(list)
        for nid, comp in zip_longest(self.node_id, self.component):
            comp_to_nids[comp].append(nid)

        #bdf_file.write(comment)
        if self.type in {'ASET', 'BSET', 'CSET', 'QSET',
                         'ASET1', 'BSET1', 'CSET1', 'QSET1'}:
            class_name = self.type[0] + 'SET1'
        elif self.type in {'OMIT', 'OMIT1'}:
            class_name = 'OMIT1'
        else:
            raise NotImplementedError(self.type)

        for comp, nids in comp_to_nids.items():
            node_id = array_str(np.array(nids), size=size).tolist()
            list_fields = [class_name, comp, ] + node_id
            bdf_file.write(print_card(list_fields))
        return

    #def index(self, node_id: np.ndarray, safe: bool=False) -> np.ndarray:
        #assert len(self.node_id) > 0, self.node_id
        #node_id = np.atleast_1d(np.asarray(node_id, dtype=self.node_id.dtype))
        #inid = np.searchsorted(self.node_id, node_id)
        #if safe:
            #ibad = inid >= len(self.node_id)
            #if sum(ibad):
                ##self.model.log.error(f'bad nids; node_id={node_id[ibad]}')
                #raise RuntimeError(f'bad nids; node_id={node_id[ibad]}')
            #inids_leftover = inid[~ibad]
            #if len(inids_leftover):
                #actual_nids = self.node_id[inids_leftover]
                #assert np.array_equal(actual_nids, node_id)
        #return inid

class ASET(ABCOQSET):
    pass
class BSET(ABCOQSET):
    pass
class CSET(ABCOQSET):
    pass
class QSET(ABCOQSET):
    pass
class OMIT(ABCOQSET):
    pass

class SUPORT(VectorizedBaseCard):
    """
    Defines determinate reaction degrees-of-freedom in a free body.

    +---------+-----+-----+-----+-----+-----+-----+-----+----+
    |    1    |  2  |  3  |  4  |  5  |  6  |  7  |  8  | 9  |
    +=========+=====+=====+=====+=====+=====+=====+=====+====+
    | SUPORT  | ID1 | C1  | ID2 |  C2 | ID3 | C3  | ID4 | C4 |
    +---------+-----+-----+-----+-----+-----+-----+-----+----+

    Defines determinate reaction degrees-of-freedom (r-set) in a free
    body-analysis.  SUPORT1 must be requested by the SUPORT1 Case
    Control command.

    +---------+-----+-----+----+-----+----+-----+----+
    |    1    |  2  |  3  |  4 |  5  | 6  |  7  | 8  |
    +=========+=====+=====+====+=====+====+=====+====+
    | SUPORT1 | SID | ID1 | C1 | ID2 | C2 | ID3 | C3 |
    +---------+-----+-----+----+-----+----+-----+----+
    | SUPORT1 |  1  |  2  | 23 |  4  | 15 |  5  |  0 |
    +---------+-----+-----+----+-----+----+-----+----+

    """
    _id_name = 'suport_id'
    def __init__(self, model: BDF):
        super().__init__(model)
        #self._is_sorted = False
        self.suport_id = np.array([], dtype='int32')
        self.component = np.array([], dtype='int32')
        self.node_id = np.array([], dtype='int32')

    def add_set(self, nids: list[int], components: list[int],
                comment: str='') -> int:
        assert isinstance(nids, (list, np.ndarray, tuple))
        assert isinstance(components, (list, np.ndarray, tuple))
        nnodes = len(nids)
        ncomp = len(components)
        assert nnodes == ncomp, (nnodes, ncomp)
        suport_id = 0
        self.cards.append((suport_id, nids, components, comment))
        #if comment:
            #self.comment[nid] = _format_comment(comment)
        self.n += nnodes
        return self.n

    def add_set1(self, suport_id: int, nids: list[int], component: list[int],
                  comment: str='') -> int:
        assert isinstance(component, (str, integer_types)), component
        nids = expand_thru(nids, set_fields=True, sort_fields=False)
        nnodes = len(nids)
        components = [component] * nnodes
        self.cards.append((suport_id, nids, components, comment))
        #if comment:
            #self.comment[nid] = _format_comment(comment)
        self.n += nnodes
        return self.n

    def add_card(self, card: BDFCard, comment: str=''):
        card_name = card[0].upper()
        msg = f'add_card(...) has been removed for {card_name}.  Use add_set_card or add_set1_card'
        raise AttributeError(msg)

    def add_set_card(self, card: BDFCard, comment: str='') -> int:
        if self.debug:
            self.model.log.debug(f'adding card {card}')

        nfields = len(card)
        assert len(card) > 1, card
        nterms = nfields // 2
        n = 1
        nodes = []
        components = []
        for i in range(nterms):
            nstart = 1 + 2 * i
            nid = integer(card, nstart, 'ID%s' % n)
            component_str = fcomponents_or_blank(card, nstart + 1, 'component%s' % n, '0')
            component = int(component_str)
            nodes.append(nid)
            components.append(component)
            n += 1

        suport_id = 0
        self.cards.append((suport_id, nodes, components, comment))
        #if comment:
            #self.comment[nid] = comment
        self.n += len(nodes)
        return self.n

    def add_set1_card(self, card: BDFCard, comment: str='') -> int:
        if self.debug:
            self.model.log.debug(f'adding card {card}')

        suport_id = integer(card, 1, 'suport_id')

        nfields = len(card)
        assert len(card) > 2
        nterms = int((nfields - 1.) / 2.)
        n = 1
        nodes = []
        components = []
        for i in range(nterms):
            nstart = 2 + 2 * i
            nid = integer(card, nstart, 'ID%s' % n)
            component_str = fcomponents_or_blank(card, nstart + 1, 'component%s' % n, '0')
            component = int(component_str)
            nodes.append(nid)
            components.append(component)
            n += 1
        #return cls(ids, components, comment=comment)

        self.cards.append((suport_id, nodes, components, comment))
        #if comment:
            #self.comment[nid] = comment
        self.n += len(nodes)
        return self.n

    @VectorizedBaseCard.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)
        if self.debug:
            self.model.log.debug(f'parse {self.type}')

        try:
            suport_id, node_id, component = self._setup(ncards, self.cards, 'int32')
        except OverflowError:
            suport_id, node_id, component = self._setup(ncards, self.cards, 'int64')
        self._save(suport_id, node_id, component)

        self.sort()
        self.cards = []

    def _setup(self, ncards: int, cards: list[Any],
               idtype: str) -> tuple[np.ndarray, np.ndarray]:
        suport_id = []
        node_id = []
        component_list = []
        #comment = {}
        for i, card in enumerate(cards):
            (suport_idi, nidi, componenti, commenti) = card
            assert isinstance(nidi, list), nidi
            assert isinstance(componenti, list), componenti
            nnodes = len(nidi)
            suport_id.extend([suport_idi]*nnodes)
            node_id.extend(nidi)
            component_list.extend(componenti)
            #if commenti:
                #comment[i] = commenti
                #comment[nidi] = commenti
        suport_id2 = np.array(suport_id, dtype=idtype)
        node_id2 = np.array(node_id, dtype=idtype)
        component2 = np.array(component_list, dtype=idtype)
        return suport_id2, node_id2, component2

    def _save(self,
              suport_id: np.ndarray,
              node_id: np.ndarray,
              component: np.ndarray,
              comment: dict[int, str]=None) -> None:
        #ncards = len(node_id)
        ncards_existing = len(self.node_id)

        if ncards_existing != 0:
            suport_id = np.hstack([self.suport_id, suport_id])
            node_id = np.hstack([self.node_id, node_id])
            component = np.hstack([self.component, component])
        #if comment:
            #self.comment.update(comment)
        self.suport_id = suport_id
        self.node_id = node_id
        self.component = component
        #print(node_id, component)
        self.n = len(node_id)
        #self.sort()
        #self.cards = []

    #def slice_by_node_id(self, node_id: np.ndarray) -> GRID:
        #inid = self._node_index(node_id)
        #return self.slice_card(inid)

    #def slice_card_by_node_id(self, node_id: np.ndarray) -> GRID:
        #"""uses a node_ids to extract GRIDs"""
        #inid = self.index(node_id)
        ##assert len(self.node_id) > 0, self.node_id
        ##i = np.searchsorted(self.node_id, node_id)
        #grid = self.slice_card_by_index(inid)
        #return grid

    #def slice_card_by_index(self, i: np.ndarray) -> GRID:
        #"""uses a node_index to extract GRIDs"""
        #assert self.xyz.shape == self._xyz_cid0.shape
        #assert len(self.node_id) > 0, self.node_id
        #i = np.atleast_1d(np.asarray(i, dtype=self.node_id.dtype))
        #i.sort()
        #grid = GRID(self.model)
        #self.__apply_slice__(grid, i)
        #return grid

    def index(self, ids: np.ndarray,
              assume_sorted: bool=True,
              check_index: bool=True,
              inverse: bool=False) -> np.ndarray:
        """
        Parameters
        ----------
        ids: (n,) int array
            the node/element/property/material/etc. ids
        assume_sorted: bool; default=True
            assume the parent array (e.g., elem.element_id is sorted)
        check_index: bool; default=True
            validate the lookup
        inverse: bool; default=False
            False: get the indices for the ids
            True: get the inverse indices for the ids

        Returns
        -------
        index: (n,) int array
            the indicies in the node_ids array (or other array)

        Example
        -------
        >>> all_ids   = [1, 2, 3, 4, 5]
        >>> all_index = [0, 1, 2, 3, 4]
        >>> ids = [3, 4]
        >>> index(all_ids, ids, inverse=False)
        [2, 3]
        >>> index(all_ids, ids, inverse=True)
        [0, 1, 4]

        """
        #if not assume_sorted:
            #self.sort()
        self_ids = self._ids
        assert len(self_ids) > 0, f'{self.type}: {self._id_name}={self_ids}'
        if ids is None:
            return None # np.arange(len(ids), dtype='int32')
        ids = np.atleast_1d(np.asarray(ids, dtype=self_ids.dtype))

        ielem = np.array([
            ii for ii, suport_idi in enumerate(self.suport_id)
            if suport_idi in ids])
        #ielem = np.searchsorted(self_ids, ids)

        if check_index:
            actual_ids = self_ids[ielem]
            if not np.array_equal(actual_ids, ids):
                raise KeyError(f'{self.type}: expected_{self._id_name}={ids}; actual_{self._id_name}={actual_ids}')
        if inverse:
            i = np.arange(len(self_ids), dtype=self_ids.dtype)
            index = np.setdiff1d(i, ielem)
            return index
        return ielem

    def __apply_slice__(self, suport: SUPORT, i: np.ndarray) -> None:
        self._slice_comment(suport, i)
        suport.n = len(i)
        suport.suport_id = self.suport_id[i]
        suport.node_id = self.node_id[i]
        suport.component = self.component[i]

    def geom_check(self, missing: dict[str, np.ndarray]):
        nid = self.model.grid.node_id
        geom_check(self,
                   missing,
                   node=(nid, self.node_id),)

    @parse_node_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        max_int = self.node_id.max()
        size = update_field_size(max_int, size)
        print_card = get_print_card_8_16(size)

        suport_id_to_nid_comp = defaultdict(list)
        for suport_idi, nid, comp in zip_longest(self.suport_id, self.node_id, self.component):
            suport_id_to_nid_comp[suport_idi].append((nid, comp))

        for suport_id, nid_comps in suport_id_to_nid_comp.items():
            if suport_id == 0:
                list_fields = ['SUPORT']
                for (nid, comp) in nid_comps:
                    list_fields += [nid, comp]

                    if len(list_fields) == 9:
                        bdf_file.write(print_card(list_fields))
                        list_fields = ['SUPORT']
                if len(list_fields) > 1:
                    bdf_file.write(print_card(list_fields))
            else:
                list_fields = ['SUPORT1', suport_id]
                for (nid, comp) in nid_comps:
                    list_fields += [nid, comp]

                    if len(list_fields) == 8:
                        bdf_file.write(print_card(list_fields))
                        list_fields = ['SUPORT1', suport_id]
                if len(list_fields):
                    bdf_file.write(print_card(list_fields))
        return

    #def index(self, node_id: np.ndarray, safe: bool=False) -> np.ndarray:
        #assert len(self.node_id) > 0, self.node_id
        #node_id = np.atleast_1d(np.asarray(node_id, dtype=self.node_id.dtype))
        #inid = np.searchsorted(self.node_id, node_id)
        #if safe:
            #ibad = inid >= len(self.node_id)
            #if sum(ibad):
                ##self.model.log.error(f'bad nids; node_id={node_id[ibad]}')
                #raise RuntimeError(f'bad nids; node_id={node_id[ibad]}')
            #inids_leftover = inid[~ibad]
            #if len(inids_leftover):
                #actual_nids = self.node_id[inids_leftover]
                #assert np.array_equal(actual_nids, node_id)
        #return inid


class USET(VectorizedBaseCard):
    _id_name = 'name'
    def __init__(self, model: BDF):
        super().__init__(model)
        #self._is_sorted = False
        self.name = np.array([], dtype='|U8')
        self.component = np.array([], dtype='int32')
        self.node_id = np.array([], dtype='int32')

    def add_set(self, name: str, nids: list[int], components: list[int],
                comment: str='') -> int:
        assert isinstance(nids, (list, np.ndarray, tuple))
        assert isinstance(components, (list, np.ndarray, tuple))
        nnodes = len(nids)
        ncomp = len(components)
        assert nnodes == ncomp, (nnodes, ncomp)
        self.cards.append((name, nids, components, comment))
        #if comment:
            #self.comment[nid] = _format_comment(comment)
        self.n += nnodes
        return self.n

    def add_set1(self, name: str, nids: list[int], component: list[int],
                  comment: str='') -> int:
        assert isinstance(component, (str, integer_types)), component
        nids = expand_thru(nids, set_fields=True, sort_fields=False)
        nnodes = len(nids)
        components = [component] * nnodes
        self.cards.append((name, nids, components, comment))
        #if comment:
            #self.comment[nid] = _format_comment(comment)
        self.n += nnodes
        return self.n

    def add_card(self, card: BDFCard, comment: str=''):
        card_name = card[0].upper()
        msg = f'add_card(...) has been removed for {card_name}.  Use add_set_card or add_set1_card'
        raise AttributeError(msg)

    def add_set_card(self, card: BDFCard, comment: str='') -> int:
        if self.debug:
            self.model.log.debug(f'adding card {card}')

        name = string(card, 1, 'name')
        nodes = []
        components = []
        nsets = (len(card) - 1) // 2
        for iset in range(nsets):
            i = iset * 2 + 2
            idi = integer(card, i, 'node_id' + str(iset))
            component = parse_components(card, i + 1, 'component' + str(iset))
            components.append(component)
            nodes.append(idi)

        self.cards.append((name, nodes, components, comment))
        #if comment:
            #self.comment[nid] = comment
        self.n += len(nodes)
        return self.n

    def add_set1_card(self, card: BDFCard, comment: str='') -> int:
        """
        Adds a USET1 card from ``BDF.add_card(...)``

        Parameters
        ----------
        card : BDFCard()
            a BDFCard object
        comment : str; default=''
            a comment for the card

        """
        if self.debug:
            self.model.log.debug(f'adding card {card}')

        name = string(card, 1, 'name')
        component = fcomponents_or_blank(card, 2, 'components', default='0')

        i = 1
        nfields = len(card)
        nodes = []
        for ifield in range(3, nfields):
            idi = integer_string_or_blank(card, ifield, 'ID%i' % i)
            if idi:
                i += 1
                nodes.append(idi)
        #return USET1(name, nodes, components, comment=comment)

        nodes = expand_thru(nodes, set_fields=True, sort_fields=True)
        nnodes = len(nodes)
        components = [component] * nnodes
        assert len(nodes) == len(components)
        self.cards.append((name, nodes, components, comment))
        #if comment:
            #self.comment[nid] = comment
        self.n += len(nodes)
        return self.n

    @VectorizedBaseCard.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)
        if self.debug:
            self.model.log.debug(f'parse {self.type}')

        try:
            name, node_id, component = self._setup(ncards, self.cards, 'int32')
        except OverflowError:
            name, node_id, component = self._setup(ncards, self.cards, 'int64')
        self._save(name, node_id, component)

        self.sort()
        self.cards = []

    def _setup(self, ncards: int, cards: list[Any],
               idtype: str) -> tuple[np.ndarray, np.ndarray]:

        name = []
        node_id = []
        component_list = []
        #comment = {}
        for i, card in enumerate(cards):
            (namei, nidi, componenti, commenti) = card
            assert isinstance(nidi, list), nidi
            assert isinstance(componenti, list), componenti
            #nidi = expand_thru(nidi, set_fields=True, sort_fields=True)
            nnodes = len(nidi)
            name.extend([namei]*nnodes)
            node_id.extend(nidi)
            component_list.extend(componenti)
            #if commenti:
                #comment[i] = commenti
                #comment[nidi] = commenti
        name2 = np.array(name, dtype='|U8')
        node_id2 = np.array(node_id, dtype=idtype)
        component2 = np.array(component_list, dtype=idtype)
        return name2, node_id2, component2

    def _save(self,
              name: np.ndarray,
              node_id: np.ndarray,
              component: np.ndarray,
              comment: dict[int, str]=None) -> None:
        #ncards = len(node_id)
        ncards_existing = len(self.node_id)
        assert len(name) == len(node_id)
        assert len(name) == len(component)
        if ncards_existing != 0:
            name = np.hstack([self.name, name])
            node_id = np.hstack([self.node_id, node_id])
            component = np.hstack([self.component, component])
        #if comment:
            #self.comment.update(comment)
        self.name = name
        self.node_id = node_id
        self.component = component
        #print(node_id, component)
        self.n = len(node_id)
        #self.sort()
        #self.cards = []

    #def slice_by_node_id(self, node_id: np.ndarray) -> GRID:
        #inid = self._node_index(node_id)
        #return self.slice_card(inid)

    #def slice_card_by_node_id(self, node_id: np.ndarray) -> GRID:
        #"""uses a node_ids to extract GRIDs"""
        #inid = self.index(node_id)
        ##assert len(self.node_id) > 0, self.node_id
        ##i = np.searchsorted(self.node_id, node_id)
        #grid = self.slice_card_by_index(inid)
        #return grid

    #def slice_card_by_index(self, i: np.ndarray) -> GRID:
        #"""uses a node_index to extract GRIDs"""
        #assert self.xyz.shape == self._xyz_cid0.shape
        #assert len(self.node_id) > 0, self.node_id
        #i = np.atleast_1d(np.asarray(i, dtype=self.node_id.dtype))
        #i.sort()
        #grid = GRID(self.model)
        #self.__apply_slice__(grid, i)
        #return grid

    def _index(self, ids: np.ndarray,
              assume_sorted: bool=True,
              check_index: bool=True,
              inverse: bool=False) -> np.ndarray:
        """
        Parameters
        ----------
        ids: (n,) int array
            the node/element/property/material/etc. ids
        assume_sorted: bool; default=True
            assume the parent array (e.g., elem.element_id is sorted)
        check_index: bool; default=True
            validate the lookup
        inverse: bool; default=False
            False: get the indices for the ids
            True: get the inverse indices for the ids

        Returns
        -------
        index: (n,) int array
            the indicies in the node_ids array (or other array)

        Example
        -------
        >>> all_ids   = [1, 2, 3, 4, 5]
        >>> all_index = [0, 1, 2, 3, 4]
        >>> ids = [3, 4]
        >>> index(all_ids, ids, inverse=False)
        [2, 3]
        >>> index(all_ids, ids, inverse=True)
        [0, 1, 4]

        """
        if not assume_sorted:
            self.sort()
        self_ids = self._ids
        assert len(self_ids) > 0, f'{self.type}: {self._id_name}={self_ids}'
        if ids is None:
            return None # np.arange(len(ids), dtype='int32')
        ids = np.atleast_1d(np.asarray(ids, dtype=self_ids.dtype))

        ielem = np.array([
            ii for ii, suport_idi in enumerate(ids)
            if suport_idi in self.suport_id])
        #ielem = np.searchsorted(self_ids, ids)

        if check_index:
            actual_ids = self_ids[ielem]
            if not np.array_equal(actual_ids, ids):
                raise KeyError(f'{self.type}: expected_{self._id_name}={ids}; actual_{self._id_name}={actual_ids}')
        if inverse:
            i = np.arange(len(self_ids), dtype=self_ids.dtype)
            index = np.setdiff1d(i, ielem)
            return index
        return ielem

    def __apply_slice__(self, name: USET, i: np.ndarray) -> None:
        self._slice_comment(name, i)
        name.n = len(i)
        name.name = self.name[i]
        name.node_id = self.node_id[i]
        name.component = self.component[i]

    def geom_check(self, missing: dict[str, np.ndarray]):
        nid = self.model.grid.node_id
        geom_check(self,
                   missing,
                   node=(nid, self.node_id),)

    @parse_node_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        max_int = self.node_id.max()
        size = update_field_size(max_int, size)
        print_card = get_print_card_8_16(size)

        name_to_nid_comp = defaultdict(list)
        for name in np.unique(self.name):
            name_to_nid_comp[name] = defaultdict(list)
        for name, nid, comp in zip_longest(self.name, self.node_id, self.component):
            name_to_nid_comp[name][comp].append(nid)

        for name, nid_comps in name_to_nid_comp.items():
            for comp, nids in nid_comps.items():
                nids.sort()
                list_fields = ['USET1', name, comp] + nids
                bdf_file.write(print_card(list_fields))
        return

    #def index(self, node_id: np.ndarray, safe: bool=False) -> np.ndarray:
        #assert len(self.node_id) > 0, self.node_id
        #node_id = np.atleast_1d(np.asarray(node_id, dtype=self.node_id.dtype))
        #inid = np.searchsorted(self.node_id, node_id)
        #if safe:
            #ibad = inid >= len(self.node_id)
            #if sum(ibad):
                ##self.model.log.error(f'bad nids; node_id={node_id[ibad]}')
                #raise RuntimeError(f'bad nids; node_id={node_id[ibad]}')
            #inids_leftover = inid[~ibad]
            #if len(inids_leftover):
                #actual_nids = self.node_id[inids_leftover]
                #assert np.array_equal(actual_nids, node_id)
        #return inid


class SET1(VectorizedBaseCard):
    """
    Defines a list of structural grid points or element identification
    numbers.

    +------+--------+--------+-----+------+-----+-----+------+-----+
    |  1   |    2   |    3   |  4  |   5  |  6  |  7  |   8  |  9  |
    +======+========+========+=====+======+=====+=====+======+=====+
    | SET1 |  SID   |   ID1  | ID2 | ID3  | ID4 | ID5 | ID6  | ID7 |
    +------+--------+--------+-----+------+-----+-----+------+-----+
    |      |  ID8   |  etc.  |     |      |     |     |      |     |
    +------+--------+--------+-----+------+-----+-----+------+-----+
    | SET1 |   3    |   31   | 62  |  93  | 124 | 16  |  17  | 18  |
    +------+--------+--------+-----+------+-----+-----+------+-----+
    |      |   19   |        |     |      |     |     |      |     |
    +------+--------+--------+-----+------+-----+-----+------+-----+
    | SET1 |   6    |   29   | 32  | THRU | 50  | 61  | THRU | 70  |
    +------+--------+--------+-----+------+-----+-----+------+-----+
    |      |   17   |   57   |     |      |     |     |      |     |
    +------+--------+--------+-----+------+-----+-----+------+-----+
    """
    _id_name = 'set_id'
    def __init__(self, model: BDF):
        super().__init__(model)
        self.set_id = np.array([], dtype='int32')
        self.is_skin = np.array([], dtype='bool')
        self.ids = np.array([], dtype='int32')
        self.num_ids = np.array([], dtype='int32')

    def slice_card_by_set_id(self, ids: np.ndarray) -> SET1:
        assert self.n > 0, self.n
        assert len(self.set_id) > 0, self.set_id
        i = self.index(ids)
        cls_obj = self.slice_card_by_index(i)
        assert cls_obj.n > 0, cls_obj
        return cls_obj

    def __apply_slice__(self, set_card: SET1, i: np.ndarray) -> None:
        #print('set_id', self.set_id)
        #print('is_skin', self.is_skin)
        #print('num_ids', self.num_ids)
        #print('ids', self.ids)
        #print('i = ', i)
        #self.set_id = np.zeros(ncards, dtype='int32')
        #self.is_skin = np.zeros(ncards, dtype='bool')
        #self.num_ids = np.zeros(ncards, dtype='int32')
        #self.ids = np.array([], dtype='int32')

        set_card.set_id = self.set_id[i]
        set_card.is_skin = self.is_skin[i]

        inid = self.inid
        set_card.ids = hslice_by_idim(i, inid, self.ids)
        set_card.num_ids = self.num_ids[i]
        set_card.n = len(self.set_id)
        #print('--------------------------------------')
        #print(self)
        #print('set_id', set_card.set_id)
        #print('is_skin', set_card.is_skin)
        #print('num_ids', set_card.num_ids)
        #print('ids', set_card.ids)
        assert set_card.n > 0, set_card.set_id

    def add(self, sid: int, ids: list[int], is_skin: bool=False,
            comment: str='') -> int:
        """
        Creates a SET1 card, which defines a list of structural grid
        points or element identification numbers.

        Parameters
        ----------
        sid : int
            set id
        ids : list[int, str]
            AECOMP, SPLINEx, PANEL : all grid points must exist
            XYOUTPUT : missing grid points are ignored
            The only valid string is THRU
            ``ids = [1, 3, 5, THRU, 10]``
        is_skin : bool; default=False
            if is_skin is used; ids must be empty
        comment : str; default=''
            a comment for the card

        """
        self.cards.append((sid, is_skin, ids, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        """
        Adds a SET1 card from ``BDF.add_card(...)``

        Parameters
        ----------
        card : BDFCard()
            a BDFCard object
        comment : str; default=''
            a comment for the card

        """
        sid = integer(card, 1, 'sid')
        ids = fields(integer_or_string, card, 'ID', i=2, j=len(card))
        is_skin = False
        i = 0
        if len(ids) > 0:
            if isinstance(ids[0], str) and ids[0] == 'SKIN':
                is_skin = True
                i += 1
        else:
            assert len(card) > 2, card
        self.cards.append((sid, is_skin, ids[i:], comment))
        #return SET1(sid, ids[i:], is_skin=is_skin, comment=comment)
        self.n += 1
        return self.n

    @VectorizedBaseCard.parse_cards_check
    def parse_cards(self):
        ncards = len(self.cards)
        idtype = self.model.idtype

        set_id = np.zeros(ncards, dtype='int32')
        is_skin = np.zeros(ncards, dtype='bool')
        num_ids = np.zeros(ncards, dtype='int32')
        #ids = np.array([], dtype='int32')

        all_ids = []
        for icard, card in enumerate(self.cards):
            sid, is_skini, idsi, comment = card
            set_id[icard] = sid
            is_skin[icard] = is_skini
            ids2 = expand_thru(idsi)
            num_ids[icard] = len(ids2)
            all_ids.extend(ids2)
        ids = np.array(all_ids, dtype=idtype)
        self._save(set_id, is_skin, num_ids, ids)
        self.sort()
        self.cards = []

    def _save(self, set_id, is_skin, num_ids, ids):
        self.set_id = set_id
        self.is_skin = is_skin
        self.num_ids = num_ids
        self.ids = ids
        self.n = len(set_id)

    def sort(self) -> None:
        usid = np.unique(self.set_id)
        if np.array_equal(usid, self.set_id):
            return
        i = np.argsort(self.set_id)
        self.__apply_slice__(self, i)

    def __apply_slice__(self, set_card: SET1, i: np.ndarray) -> None:
        assert self.num_ids.sum() == len(self.ids)
        set_card.n = len(i)
        set_card.set_id = self.set_id[i]
        set_card.is_skin = self.is_skin[i]

        inid = self.inid # [i, :]
        set_card.dims = hslice_by_idim(i, inid, self.ids)

        set_card.num_ids = self.num_ids[i]
        #assert isinstance(prop.ndim, np.ndarray), prop.ndim
        #assert prop.ndim.sum() == len(prop.dims), f'prop.ndim={prop.ndim} len(prop.dims)={len(prop.dims)}'

    def geom_check(self, missing: dict[str, np.ndarray]):
        pass

    @property
    def inid(self) -> np.ndarray:
        return make_idim(self.n, self.num_ids)

    #@parse_node_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        if len(self.set_id) == 0:
            return
        max_int = self.set_id.max()
        size = update_field_size(max_int, size)
        print_card = get_print_card_8_16(size)

        set_ids = array_str(self.set_id, size=size)
        ids_ = array_str(self.ids, size=size).tolist()
        for sid, is_skin, inid in zip(set_ids, self.is_skin, self.inid):
            inid0, inid1 = inid
            ids = ids_[inid0:inid1]

            # checked in NX 2014 / MSC 2005.1
            if is_skin:
                list_fields = ['SET1', sid, 'SKIN'] + ids
            else:
                list_fields = ['SET1', sid] + ids

            # I thought this worked in the new MSC Nastran...
            # Doesn't work in NX 2014 / MSC 2005.1 (multiple duplicate sids).
            # It may work with one sid, with singles and doubles on one card.
            #field_packs = []
            #singles, doubles = collapse_thru_packs(self.get_ids())
            #if singles:
                #field_packs.append(['SET1', self.sid] + skin + singles)
            #if doubles:
                #for pack in doubles:
                    #field_packs.append(['SET1', self.sid] + skin + pack)

            bdf_file.write(print_card(list_fields))
        return


