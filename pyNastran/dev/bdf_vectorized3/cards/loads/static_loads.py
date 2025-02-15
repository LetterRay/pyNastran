from __future__ import annotations
from collections import defaultdict
from itertools import zip_longest
from typing import Union, TYPE_CHECKING
import numpy as np

from pyNastran.bdf.cards.base_card import expand_thru_by
from pyNastran.bdf.field_writer_8 import set_string8_blank_if_default, print_float_8 # , print_card_8, print_field_8
#from pyNastran.bdf.field_writer_16 import print_card_16 # , print_scientific_16, print_field_16
#from pyNastran.bdf.field_writer_double import print_scientific_double
from pyNastran.bdf.bdf_interface.assign_type import (
    integer, double,
    integer_or_blank, double_or_blank,
    components_or_blank,
    string, integer_or_string, fields,
)
from pyNastran.bdf.cards.collpase_card import collapse_thru_by
#from pyNastran.bdf.bdf_interface.assign_type_force import force_integer
from pyNastran.utils.numpy_utils import (
    integer_types, float_types,   # integer_float_types,
)

from pyNastran.dev.bdf_vectorized3.bdf_interface.geom_check import geom_check
from pyNastran.dev.bdf_vectorized3.cards.coord import transform_spherical_to_rectangular
from pyNastran.dev.bdf_vectorized3.cards.base_card import (
    VectorizedBaseCard, hslice_by_idim, make_idim,
    parse_load_check, get_print_card_8_16) # , searchsorted_filter
from pyNastran.dev.bdf_vectorized3.cards.write_utils import (
    array_str, array_float, array_default_int)

if TYPE_CHECKING:  # pragma: no cover
    from pyNastran.dev.bdf_vectorized3.types import TextIOLike
    from pyNastran.dev.bdf_vectorized3.bdf import BDF
    from pyNastran.bdf.bdf_interface.bdf_card import BDFCard
    from .dynamic_loads import LOADSET


class Load(VectorizedBaseCard):
    _id_name = 'load_id'
    def __init__(self, model: BDF):
        super().__init__(model)
        self.load_id = np.array([], dtype='int32')

    def _geom_check(self) -> None:
        pass

    def slice_card_by_load_id(self, load_id: np.ndarray) -> Load0:
        assert len(self.load_id) > 0, self
        card_class = self.__class__
        card = card_class(self.model)
        if isinstance(load_id, integer_types):
            load_id_set = {load_id}
        else:
            load_id_set = set(load_id.tolist())

        index = []
        for i, load_idi in enumerate(self.load_id):
            if load_idi in load_id_set:
                index.append(i)
        assert len(index) > 0, f'no {card.type}s found; {self} load_id={load_id} load_ids={self.load_id}'
        return self.slice_card_by_index(index)


class DEFORM(Load):
    """
    Defines an enforced displacement value for static analysis.

     +--------+-----+-----+------+----+----+----+----+
     |    1   |  2  |  3  |   5  |  6 |  8 |  6 |  8 |
     +========+=====+=====+======+====+====+====+====+
     | DEFORM | SID |  E1 |  D1  | E2 | D2 | E3 | D3 |
     +--------+-----+-----+------+----+----+----+----+
     | DEFORM | 100 | 32  | -2.6 | 5  | .9 | 6  | .9 |
     +--------+-----+-----+------+----+----+----+----+
    """
    def slice_card_by_index(self, i: np.ndarray) -> DEFORM:
        load = DEFORM(self.model)
        self.__apply_slice__(load, i)
        return load

    def __apply_slice__(self, load: DEFORM, i: np.ndarray) -> None:
        load.n = len(i)
        load.load_id = self.load_id[i]
        load.elements = self.elements[i]
        load.enforced = self.enforced[i]

    def add(self, sid: int, eid: int, deformation: float,
            comment: str='') -> int:
        """
        Creates an DEFORM card, which defines applied deformation on
        a 1D element.  Links to the DEFORM card in the case control
        deck.

        Parameters
        ----------
        sid : int
            load id
        eid : int
            CTUBE/CROD/CONROD/CBAR/CBEAM element id
        deformation : float
            the applied deformation
        comment : str; default=''
            a comment for the card

        """
        self.cards.append((sid, eid, deformation, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        """
        Adds a DEFORM card from ``BDF.add_card(...)``

        Parameters
        ----------
        card : BDFCard()
            a BDFCard object
        comment : str; default=''
            a comment for the card

        """
        sid = integer(card, 1, 'sid')
        eid = integer(card, 2, 'eid1')
        deformation = double(card, 3, 'D1')
        self.cards.append((sid, eid, deformation, comment))
        comment = ''
        self.n += 1
        if card.field(4):
            eid = integer(card, 4, 'eid2')
            deformation = double(card, 5, 'D2')
            self.cards.append((sid, eid, deformation, comment))
            self.n += 1
        if card.field(6):
            eid = integer(card, 6, 'eid3')
            deformation = double(card, 7, 'D3')
            self.cards.append((sid, eid, deformation, comment))
            self.n += 1
        return self.n


    @Load.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)
        load_id = np.zeros(ncards, dtype='int32')
        elements = np.zeros(ncards, dtype='int32')
        enforced = np.zeros(ncards, dtype='float64')
        for icard, card in enumerate(self.cards):
            (sid, eid, enforcedi, comment) = card
            load_id[icard] = sid
            elements[icard] = eid
            enforced[icard] = enforcedi
        self._save(load_id, elements, enforced)
        self.sort()
        self.cards = []

    def _save(self, load_id, elements, enforced):
        self.load_id = load_id
        self.elements = elements
        self.enforced = enforced

    def geom_check(self, missing: dict[str, np.ndarray]):
        """CTUBE/CROD/CONROD/CBAR/CBEAM"""
        model = self.model
        line_element_cards = (
                model.ctube, model.crod, model.conrod,
                model.cbar, model.cbeam)
        line_element_ids = np.hstack([
            elem.element_id for elem in line_element_cards
            if elem.n])
        uelements = np.unique(line_element_ids)
        geom_check(self,
                   missing,
                   element_id=(uelements, self.elements))

    @parse_load_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        print_card = get_print_card_8_16(size)

        load_ids = array_str(self.load_id, size=size)
        elements = array_str(self.elements, size=size)
        for load_id, eid, enforced in zip(load_ids, elements, self.enforced):
            fields = ['DEFORM', load_id, eid, enforced]
            bdf_file.write(print_card(fields))
        return


class SPCD(Load):
    """
    Defines an enforced displacement value for static analysis and an
    enforced motion value (displacement, velocity or acceleration) in
    dynamic analysis.

     +------+-----+-----+-----+------+----+----+----+
     |   1  |  2  |  3  |  4  |   5  |  6 | 7  |  8 |
     +======+=====+=====+=====+======+====+====+====+
     | SPCD | SID |  G1 | C1  |  D1  | G2 | C2 | D2 |
     +------+-----+-----+-----+------+----+----+----+
     | SPCD | 100 | 32  | 436 | -2.6 | 5  | 2  | .9 |
     +------+-----+-----+-----+------+----+----+----+
    """
    def slice_card_by_index(self, i: np.ndarray) -> SPCD:
        load = SPCD(self.model)
        self.__apply_slice__(load, i)
        return load

    def __apply_slice__(self, load: SPCD, i: np.ndarray) -> None:
        load.n = len(i)
        load.load_id = self.load_id[i]
        load.nodes = self.nodes[i]
        load.components = self.components[i]
        load.enforced = self.enforced[i]

    def add(self, spc_id: list[int], nodes: list[int],
            components: list[int], enforced: list[float],
            comment: str='') -> int:
        """
        Creates an SPCD card, which defines the degree of freedoms to be
        set during enforced motion

        Parameters
        ----------
        spc_id : int
            constraint id
        nodes : list[int]
            GRID/SPOINT ids
        components : list[str]
            the degree of freedoms to constrain (e.g., '1', '123')
        enforced : list[float]
            the constrained value for the given node (typically 0.0)
        comment : str; default=''
            a comment for the card

        Notes
        -----
        len(nodes) == len(components) == len(enforced)

        .. warning:: Non-zero enforced deflection requires an SPC/SPC1 as well.
                     Yes, you really want to constrain the deflection to 0.0
                     with an SPC1 card and then reset the deflection using an
                     SPCD card.

        """
        if isinstance(nodes, integer_types):
            nodes = [nodes]
        nnodes = len(nodes)

        if isinstance(spc_id, integer_types):
            spc_id = [spc_id] * nnodes
        self.cards.append((spc_id, nodes, components, enforced, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        sid = integer(card, 1, 'sid')
        if card.field(5) in [None, '']:
            sids = [sid]
            nodes = [integer(card, 2, 'G1'),]
            components = [components_or_blank(card, 3, 'C1', default='0')]
            enforced = [double_or_blank(card, 4, 'D1', default=0.0)]
        else:
            sids = [sid, sid]
            nodes = [
                integer(card, 2, 'G1'),
                integer(card, 5, 'G2'),
            ]
            # :0 if scalar point 1-6 if grid
            components = [components_or_blank(card, 3, 'C1', default='0'),
                          components_or_blank(card, 6, 'C2', default='0')]
            enforced = [double_or_blank(card, 4, 'D1', default=0.0),
                        double_or_blank(card, 7, 'D2', default=0.0)]
        self.cards.append((sids, nodes, components, enforced, comment))
        self.n += 1
        return self.n

    @Load.parse_cards_check
    def parse_cards(self) -> None:
        #ncards = len(self.cards)
        load_ids = []
        all_nodes = []
        all_components = []
        all_enforced = []
        for icard, card in enumerate(self.cards):
            (sids, nodesi, componentsi, enforcedi, comment) = card
            load_ids.extend(sids)
            all_nodes.extend(nodesi)
            all_components.extend(componentsi)
            all_enforced.extend(enforcedi)
        load_id = np.array(load_ids, dtype='int32')
        nodes = np.array(all_nodes, dtype='int32')
        components = np.array(all_components, dtype='int32')
        enforced = np.array(all_enforced, dtype='float64')
        self._save(load_id, nodes, components, enforced)
        self.cards = []

    def _save(self, load_id, nodes, components, enforced):
        nloads = len(load_id)
        self.load_id = load_id
        self.nodes = nodes
        self.components = components
        self.enforced = enforced
        self.n = nloads

    @parse_load_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        print_card = get_print_card_8_16(size)
        load_ids = array_str(self.load_id, size=size)
        node_ids = array_str(self.nodes, size=size)
        components = array_default_int(self.components, default=0, size=size)
        for load_id, nid , component, enforced in zip(load_ids, node_ids, components, self.enforced):
            fields = ['SPCD', load_id, nid, component, enforced]
            bdf_file.write(print_card(fields))
        return


class Load0(Load):
    def __init__(self, model: BDF):
        super().__init__(model)
        self.node_id = np.array([], dtype='int32')
        self.coord_id = np.array([], dtype='int32')
        self.mag = np.array([], dtype='float64')
        self.xyz = np.zeros((0, 3), dtype='float64')

    def add(self, sid: int, node: int, mag: float, xyz: np.ndarray,
            cid: int=0, comment: str='') -> FORCE:
        """
        Creates a FORCE/MOMENT card

        Parameters
        ----------
        sid : int
            load id
        node : int
            the node to apply the load to
        mag : float
            the load's magnitude
        xyz : (3, ) float ndarray
            the load direction in the cid frame
        cid : int; default=0
            the coordinate system for the load
        comment : str; default=''
            a comment for the card

        """
        self.cards.append((sid, node, cid, mag, xyz, comment))
        self.n += 1

    def add_card(self, card: BDFCard, comment: str='') -> int:
        sid = integer(card, 1, 'sid')
        node = integer(card, 2, 'node')
        cid = integer_or_blank(card, 3, 'cid', default=0)
        mag = double(card, 4, 'mag')
        xyz = [double_or_blank(card, 5, 'X1', default=0.0),
               double_or_blank(card, 6, 'X2', default=0.0),
               double_or_blank(card, 7, 'X3', default=0.0)]
        assert len(card) <= 8, 'len(%s card) = %d\ncard=%s' % (self.type, len(card), card)
        self.cards.append((sid, node, cid, mag, xyz, comment))
        self.n += 1
        return self.n

    @Load.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)
        load_id = np.zeros(ncards, dtype='int32')
        node_id = np.zeros(ncards, dtype='int32')
        coord_id = np.zeros(ncards, dtype='int32')
        mag = np.zeros(ncards, dtype='float64')
        xyz = np.zeros((ncards, 3), dtype='float64')
        assert ncards > 0, ncards
        for icard, card in enumerate(self.cards):
            (sid, node, cid, magi, xyzi, comment) = card
            load_id[icard] = sid
            node_id[icard] = node
            coord_id[icard] = cid
            mag[icard] = magi
            xyz[icard, :] = xyzi
        self._save(load_id, node_id, coord_id, mag, xyz)
        assert len(load_id) == self.n
        self.cards = []

    def _save(self, load_id, node_id, coord_id, mag, xyz):
        if len(self.load_id) == 0:
            load_id = np.hstack([self.load_id, load_id])
            node_id = np.hstack([self.node_id, node_id])
            coord_id = np.hstack([self.coord_id, coord_id])
            mag = np.hstack([self.mag, mag])
            xyz = np.vstack([self.xyz, xyz])
        nloads = len(load_id)
        self.load_id = load_id
        self.node_id = node_id
        self.coord_id = coord_id
        self.mag = mag
        self.xyz = xyz
        self.n = nloads

    def geom_check(self, missing: dict[str, np.ndarray]):
        nid = self.model.grid.node_id
        cid = self.model.coord.coord_id

        #load_nodes = self.node_id
        #load_cid = self.coord_id
        #assert base_nodes is not None
        #print(self.base_nodes)
        geom_check(self,
                   missing,
                   node=(nid, self.node_id), filter_node0=False,
                   coord=(cid, self.coord_id))

    @parse_load_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        card_class = self.type
        load_ids = array_str(self.load_id, size=size)
        node_ids = array_default_int(self.node_id, default=0, size=size)
        coord_ids = array_default_int(self.coord_id, default=0, size=size)
        if size == 8:
            for sid, nid, cid, mag, xyz in zip(load_ids, node_ids, coord_ids, self.mag, self.xyz):
                msg = '%-8s%8s%8s%8s%8s%8s%8s%8s\n' % (
                    card_class, sid, nid,
                    cid, print_float_8(mag), print_float_8(xyz[0]),
                    print_float_8(xyz[1]), print_float_8(xyz[2]))
                bdf_file.write(msg)
        else:
            print_card = get_print_card_8_16(size)
            for sid, nid, cid, mag, xyz in zip(load_ids, node_ids, coord_ids, self.mag, self.xyz):
                fields = [card_class, sid, nid, cid, mag, xyz[0], xyz[1], xyz[2]]
                bdf_file.write(print_card(fields))
        return

class Load1(Load):
    def __init__(self, model: BDF):
        super().__init__(model)
        self.node_id = np.array([], dtype='int32')
        self.nodes = np.zeros((0, 2), dtype='float64')
        self.mag = np.array([], dtype='float64')
        #self.xyz = np.zeros((0, 3), dtype='float64')

    def add(self, sid: int, node: int, mag: float,
            g1: int, g2: int, comment: str='') -> int:
        """
        Creates a FORCE1/MOMENT1 card

        Parameters
        ----------
        sid : int
            load id
        node : int
            the node to apply the load to
        mag : float
            the load's magnitude
        n1 / n2 : int / int
            defines the load direction
            n = n2 - n1
        comment : str; default=''
            a comment for the card

        """
        self.cards.append((sid, node, mag, [g1, g2], comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        sid = integer(card, 1, 'sid')
        node = integer(card, 2, 'node')
        mag = double(card, 3, 'mag')
        g1 = integer(card, 4, 'g1')
        g2 = integer(card, 5, 'g2')
        assert len(card) == 6, 'len(%s card) = %i\ncard=%s' % (self.type, len(card), card)
        self.cards.append((sid, node, mag, [g1, g2], comment))
        self.n += 1
        return self.n

    @Load.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)
        load_id = np.zeros(ncards, dtype='int32')
        node_id = np.zeros(ncards, dtype='int32')
        mag = np.zeros(ncards, dtype='float64')
        nodes = np.zeros((ncards, 2), dtype='int32')
        assert ncards > 0, ncards
        for icard, card in enumerate(self.cards):
            sid, node, magi, g12, comment = card
            load_id[icard] = sid
            node_id[icard] = node
            mag[icard] = magi
            nodes[icard, :] = g12
        self._save(load_id, node_id, mag, nodes)
        assert len(self.load_id) == self.n
        self.cards = []

    def _save(self, load_id, node_id, mag, nodes):
        if len(self.load_id) != 0:
            raise NotImplementedError()
        nloads = len(load_id)
        self.load_id = load_id
        self.node_id = node_id
        self.mag = mag
        self.nodes = nodes
        self.n = nloads

    def geom_check(self, missing: dict[str, np.ndarray]):
        nid = self.model.grid.node_id
        geom_check(self,
                   missing,
                   node=(nid, self.node_id),
                   )

    @parse_load_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        card_class = self.type
        load_ids = array_str(self.load_id, size=size)
        node_id = array_default_int(self.node_id, default=0, size=size)
        node_ids = array_default_int(self.nodes, default=0, size=size)
        if size == 8:
            for sid, nid, mag, nodes in zip(load_ids, node_id, self.mag, node_ids):
                msg = '%-8s%8s%8s%8s%8s%8s\n' % (
                    card_class, sid, nid, print_float_8(mag), nodes[0], nodes[1])
                bdf_file.write(msg)
        else:
            print_card = get_print_card_8_16(size)
            for sid, nid, mag, nodes in zip(load_ids, node_id, self.mag, node_ids):
                fields = [card_class, sid, nid, mag, nodes[0], nodes[1]]
                bdf_file.write(print_card(fields))
        return


class Load2(Load):
    def __init__(self, model: BDF):
        super().__init__(model)
        self.node_id = np.array([], dtype='int32')
        self.nodes = np.zeros((0, 4), dtype='float64')
        self.mag = np.array([], dtype='float64')
        #self.xyz = np.zeros((0, 3), dtype='float64')

    def add(self, sid: int, node: int, mag: float,
            g1: int, g2: int, g3: int, g4: int,
            comment: str='') -> int:
        """
        Creates a FORCE2/MOMENT2 card

        Parameters
        ----------
        sid : int
            load id
        node : int
            the node to apply the load to
        mag : float
            the load's magnitude
        g1 / g2 / g3 / g4 : int / int / int / int
            defines the load direction
            n = (g2 - g1) x (g4 - g3)
        comment : str; default=''
            a comment for the card

        """
        self.cards.append((sid, node, mag, [g1, g2, g3, g4], comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        sid = integer(card, 1, 'sid')
        node = integer(card, 2, 'node')
        mag = double(card, 3, 'mag')
        g1 = integer(card, 4, 'g1')
        g2 = integer(card, 5, 'g2')
        g3 = integer(card, 6, 'g3')
        g4 = integer(card, 7, 'g4')
        assert len(card) == 8, 'len(%s card) = %i\ncard=%s' % (self.type, len(card), card)
        self.cards.append((sid, node, mag, [g1, g2, g3, g4], comment))
        self.n += 1
        return self.n

    def parse_cards(self) -> None:
        if self.n == 0:
            return
        ncards = len(self.cards)
        if ncards == 0:
            return
        load_id = np.zeros(ncards, dtype='int32')
        node_id = np.zeros(ncards, dtype='int32')
        mag = np.zeros(ncards, dtype='float64')
        nodes = np.zeros((ncards, 4), dtype='int32')
        assert ncards > 0, ncards
        for icard, card in enumerate(self.cards):
            (sid, node, magi, nodesi, comment) = card
            load_id[icard] = sid
            node_id[icard] = node
            mag[icard] = magi
            nodes[icard, :] = nodesi
        self._save(load_id, node_id, mag, nodes)
        assert len(self.load_id) == self.n
        self.cards = []

    def _save(self, load_id, node_id, mag, nodes):
        if len(self.load_id) != 0:
            raise NotImplementedError()
        nloads = len(load_id)
        self.load_id = load_id
        self.node_id = node_id
        self.mag = mag
        self.nodes = nodes
        self.n = nloads

    def geom_check(self, missing: dict[str, np.ndarray]):
        nid = self.model.grid.node_id
        geom_check(self,
                   missing,
                   node=(nid, self.node_id),)

        nodes = self.nodes.flatten()
        nodes = nodes[nodes != 0]
        geom_check(self,
                   missing,
                   node=(nid, nodes),)

    @parse_load_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        card_class = self.type
        load_ids = array_str(self.load_id, size=size)
        node_id_ = array_str(self.node_id, size=size)
        node_ids_ = array_default_int(self.nodes, default=0, size=size)
        if size == 8:
            for sid, nid, mag, nodes in zip(load_ids, node_id_, self.mag, node_ids_):
                msg = '%-8s%8s%8s%8s%8s%8s%8s%8s\n' % (
                    card_class, sid, nid, print_float_8(mag), nodes[0], nodes[2], nodes[1], nodes[3])
                bdf_file.write(msg)
        else:
            print_card = get_print_card_8_16(size)
            for sid, nid, mag, nodes in zip(load_ids, node_id_, self.mag, node_ids_):
                fields = [card_class, sid, nid, mag, nodes[0], nodes[2], nodes[1], nodes[3]]
                bdf_file.write(print_card(fields))
        return

class FORCE(Load0):
    def slice_card_by_index(self, i: np.ndarray) -> FORCE:
        load = FORCE(self.model)
        self.__apply_slice__(load, i)
        return load

    def __apply_slice__(self, load: FORCE, i: np.ndarray) -> None:  # ignore[override]
        load.n = len(i)
        load.load_id = self.load_id[i]
        load.node_id = self.node_id[i]
        load.coord_id = self.coord_id[i]
        load.mag = self.mag[i]
        load.xyz = self.xyz[i, :]

    @property
    def scaled_vector(self) -> np.ndarray:
        return self.mag * self.xyz

    def sum_forces_moments(self) -> np.ndarray:
        grid = self.model.grid
        xyz_cid0 = grid.xyz_cid0()
        nid = grid.node_id

        nloads = len(self.load_id)
        force_moment = np.zeros((nloads, 6), dtype='float64')
        force = force_moment[:, :3]
        moment = force_moment[:, 3:]

        ucoords = np.unique(self.coord_id)
        for cid in ucoords:
            icoord = np.where(self.coord_id == cid)[0]
            force0 = self.mag[icoord, np.newaxis] * self.xyz[icoord, :]
            moment0 = np.cross(force0, self.xyz[icoord, :])
            #print('cid =', cid)
            #print('xyz =', self.xyz[icoord, :])
            #print('force0', force0)
            #print('moment0', moment0)
            if cid == 0:
                force[icoord, :] = force0
                moment[icoord, :] = moment0
            else:
                #print('else...')
                coord = self.model.coord
                coord_card = coord.slice_card_by_coord_id(cid)
                beta = coord_card.xyz_to_global_transform[cid]

                coord_type = coord_card.coord_type
                if coord_type == 'R':
                    # TODO: I'm pretty sure this is right...
                    force[icoord, :] = force0 @ beta
                    moment[icoord, :] = moment0 @ beta
                elif coord_type == 'S':
                    # TODO: I'm pretty sure this is right...
                    force_r = np.array([transform_spherical_to_rectangular(force_) for force_ in force0])
                    moment_r = np.array([transform_spherical_to_rectangular(moment_) for moment_ in moment0])
                    force[icoord, :] = force_r @ beta
                    moment[icoord, :] = moment_r @ beta
                else:
                    raise NotImplementedError(f'coord={cid} not supported\n{coord_card.write()}')
        assert force_moment.shape == (len(self), 6), force_moment.shape
        return force_moment

class MOMENT(Load0):
    def slice_card_by_index(self, i: np.ndarray) -> MOMENT:
        load = MOMENT(self.model)
        self.__apply_slice__(load, i)
        return load

    def __apply_slice__(self, load: MOMENT, i: np.ndarray) -> None:  # ignore[override]
        load.n = len(i)
        load.load_id = self.load_id[i]
        load.node_id = self.node_id[i]
        load.coord_id = self.coord_id[i]
        load.mag = self.mag[i]
        load.xyz = self.xyz[i, :]

    @property
    def scaled_vector(self) -> np.ndarray:
        return self.mag * self.xyz

    def sum_forces_moments(self):
        grid = self.model.grid
        #xyz_cid0 = grid.xyz_cid0()
        #nid = grid.node_id

        nloads = len(self.load_id)
        ucoords = np.unique(self.coord_id)
        moment = self.mag[:, np.newaxis] * self.xyz
        #if self.coord_id.max() == 0 and self.coord_id.min() == 0:
            #moment = local_moment
        #else:

        coord =  self.model.coord
        for ucid in ucoords:
            if ucid == 0:
                continue
            icid = np.where(ucid == self.coord_id)[0]
            local_moment = moment[icid, :]
            global_moment = coord.transform_force_local_to_global(local_moment)
            moment[icid, :] = global_moment
            #coords = coord.slice_card_by_coord_id(ucoords)
            #raise NotImplementedError(f'the following coordinate systems are not supported\n{coords.write()}')

        force_moment = np.zeros((nloads, 6), dtype='float64')
        force_moment[:, 3:] = moment
        return force_moment


class FORCE1(Load1):
    """
    Defines a static concentrated force at a grid point by specification of a
    magnitude and two grid points that determine the direction.

    +--------+-----+----+-------+----+----+
    |   1    |  2  | 3  |   4   | 5  | 6  |
    +========+=====+====+=======+====+====+
    | FORCE1 | SID | G  |   F   | G1 | G2 |
    +--------+-----+----+-------+----+----+
    | FORCE1 |  6  | 13 | -2.93 | 16 | 13 |
    +--------+-----+----+-------+----+----+

    """
    def slice_card_by_index(self, i: np.ndarray) -> FORCE1:
        load = FORCE1(self.model)
        self.__apply_slice__(load, i)
        return load

    def __apply_slice__(self, load: FORCE1, i: np.ndarray) -> None:  # ignore[override]
        load.n = len(i)
        load.load_id = self.load_id[i]
        load.node_id = self.node_id[i]
        load.mag = self.mag[i]
        load.nodes = self.nodes[i, :]

    def sum_forces_moments(self):
        grid = self.model.grid
        xyz_cid0 = grid.xyz_cid0()

        nloads = len(self.load_id)
        iapplied_nid = np.searchsorted(grid.node_id, self.node_id)
        inid = np.searchsorted(grid.node_id, self.nodes)
        in1 = inid[:, 0]
        in2 = inid[:, 1]

        xyz = xyz_cid0[iapplied_nid, :]
        xyz1 = xyz_cid0[in1, :]
        xyz2 = xyz_cid0[in2, :]
        nxyz = xyz2 - xyz1
        dist = np.linalg.norm(nxyz, axis=1)

        assert len(dist) == nloads
        assert dist.min() > 0, dist
        nxyz /= dist[:, np.newaxis]

        force = self.mag[:, np.newaxis] * nxyz
        moment = np.cross(xyz, force)

        force_moment = np.hstack([force, moment])
        assert force_moment.shape == (nloads, 6)
        return force_moment

class MOMENT1(Load1):
    def slice_card_by_index(self, i: np.ndarray) -> MOMENT1:
        load = MOMENT1(self.model)
        self.__apply_slice__(load, i)
        return load

    def __apply_slice__(self, load: MOMENT1, i: np.ndarray) -> None:  # ignore[override]
        load.n = len(i)
        load.load_id = self.load_id[i]
        load.node_id = self.node_id[i]
        load.mag = self.mag[i]
        load.nodes = self.nodes[i, :]

    def sum_forces_moments(self):
        grid = self.model.grid
        xyz_cid0 = grid.xyz_cid0()

        nloads = len(self.load_id)
        iapplied_nid = np.searchsorted(grid.node_id, self.node_id)
        inid = np.searchsorted(grid.node_id, self.nodes)
        in1 = inid[:, 0]
        in2 = inid[:, 1]

        xyz = xyz_cid0[iapplied_nid, :]
        xyz1 = xyz_cid0[in1, :]
        xyz2 = xyz_cid0[in2, :]
        nxyz = xyz2 - xyz1
        dist = np.linalg.norm(nxyz, axis=1)

        assert len(dist) == nloads
        assert dist.min() > 0, dist
        nxyz /= dist[:, np.newaxis]

        moment = self.mag[:, np.newaxis] * nxyz
        force_moment = np.hstack([np.zeros((nloads, 3), dtype='float64'), moment])
        assert force_moment.shape == (nloads, 6)
        return force_moment


class FORCE2(Load2):
    def slice_card_by_index(self, i: np.ndarray) -> FORCE2:
        load = FORCE2(self.model)
        self.__apply_slice__(load, i)
        return load

    def __apply_slice__(self, load: FORCE2, i: np.ndarray) -> None:  # ignore[override]
        load.n = len(i)
        load.load_id = self.load_id[i]
        load.node_id = self.node_id[i]
        load.mag = self.mag[i]
        load.nodes = self.nodes[i, :]

    def sum_forces_moments(self):
        grid = self.model.grid
        xyz_cid0 = grid.xyz_cid0()

        nloads = len(self.load_id)
        iapplied_nid = np.searchsorted(grid.node_id, self.node_id)
        inid = np.searchsorted(grid.node_id, self.nodes)
        in1 = inid[:, 0]
        in2 = inid[:, 1]
        in3 = inid[:, 2]
        in4 = inid[:, 3]
        assert in4.min() > 0, in4

        xyz = xyz_cid0[iapplied_nid, :]
        xyz1 = xyz_cid0[in1, :]
        xyz2 = xyz_cid0[in2, :]
        xyz3 = xyz_cid0[in3, :]
        xyz4 = xyz_cid0[in4, :]

        #v21 = xyz2 - xyz1
        #v2 = xyz4 - xyz3
        #xyz = cross(v21, v2)
        nxyz = np.cross(xyz2 - xyz1, xyz4 - xyz3)
        dist = np.linalg.norm(nxyz, axis=1)

        assert len(dist) == nloads
        assert dist.min() > 0, dist
        nxyz /= dist[:, np.newaxis]

        force = self.mag[:, np.newaxis] * nxyz
        moment = np.cross(xyz, force)

        force_moment = np.hstack([force, moment])
        assert force_moment.shape == (nloads, 6)
        return force_moment

class MOMENT2(Load2):
    def slice_card_by_index(self, i: np.ndarray) -> MOMENT2:
        load = MOMENT2(self.model)
        self.__apply_slice__(load, i)
        return load

    def __apply_slice__(self, load: MOMENT2, i: np.ndarray) -> None:  # ignore[override]
        load.n = len(i)
        load.load_id = self.load_id[i]
        load.node_id = self.node_id[i]
        load.mag = self.mag[i]
        load.nodes = self.nodes[i, :]

    def sum_forces_moments(self):
        grid = self.model.grid
        xyz_cid0 = grid.xyz_cid0()

        nloads = len(self.load_id)
        iapplied_nid = np.searchsorted(grid.node_id, self.node_id)
        inid = np.searchsorted(grid.node_id, self.nodes)
        in1 = inid[:, 0]
        in2 = inid[:, 1]
        in3 = inid[:, 2]
        in4 = inid[:, 3]
        assert in4.min() > 0, in4

        xyz = xyz_cid0[iapplied_nid, :]
        xyz1 = xyz_cid0[in1, :]
        xyz2 = xyz_cid0[in2, :]
        xyz3 = xyz_cid0[in3, :]
        xyz4 = xyz_cid0[in4, :]

        #v21 = xyz2 - xyz1
        #v2 = xyz4 - xyz3
        #xyz = cross(v21, v2)
        nxyz = np.cross(xyz2 - xyz1, xyz4 - xyz3)
        dist = np.linalg.norm(nxyz, axis=1)

        assert len(dist) == nloads
        assert dist.min() > 0, dist
        nxyz /= dist[:, np.newaxis]

        moment = self.mag[:, np.newaxis] * nxyz
        force_moment = np.hstack([np.zeros((nloads, 3), dtype='float64'), moment])
        assert force_moment.shape == (nloads, 6)
        return force_moment


class GRAV(Load):
    """
    Defines acceleration vectors for gravity or other acceleration loading.

    +------+-----+-----+------+-----+-----+------+-----+
    |  1   |  2  |  3  |   4  |  5  |  6  |   7  |  8  |
    +======+=====+=====+======+=====+=====+======+=====+
    | GRAV | SID | CID |  A   | N1  | N2  |  N3  |  MB |
    +------+-----+-----+------+-----+-----+------+-----+
    | GRAV | 1   | 3   | 32.2 | 0.0 | 0.0 | -1.0 |     |
    +------+-----+-----+------+-----+-----+------+-----+

    """
    def slice_card_by_index(self, i: np.ndarray) -> GRAV:
        load = GRAV(self.model)
        self.__apply_slice__(load, i)
        return load

    def __apply_slice__(self, load: GRAV, i: np.ndarray) -> None:
        load.n = len(i)
        load.load_id = self.load_id[i]
        load.coord_id = self.coord_id[i]
        load.scale = self.scale[i]
        load.main_bulk = self.main_bulk[i]
        load.N = self.N[i, :]

    def add(self, sid: int, scale: float, N: np.ndarray,
            cid: int=0, mb: int=0, comment: str='') -> int:
        """
        Creates an GRAV card

        Parameters
        ----------
        sid : int
            load id
        scale : float
            scale factor for load
        N : (3, ) float ndarray
            the acceleration vector in the cid frame
        cid : int; default=0
            the coordinate system for the load
        mb : int; default=0
            ???
        comment : str; default=''
            a comment for the card

        """
        self.cards.append((sid, cid, scale, N, mb, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        sid = integer(card, 1, 'sid')
        cid = integer_or_blank(card, 2, 'cid', 0)
        scale = double(card, 3, 'scale')
        N = [double_or_blank(card, 4, 'N1', default=0.0),
             double_or_blank(card, 5, 'N2', default=0.0),
             double_or_blank(card, 6, 'N3', default=0.0), ]
        main_bulk = integer_or_blank(card, 7, 'mb', default=0)
        assert len(card) <= 8, f'len(GRAV card) = {len(card):d}\ncard={card}'
        #assert not np.allclose(max(abs(N)), 0.), ('GRAV N is a zero vector, '
                                                    #'N=%s' % str(self.N))
        self.cards.append((sid, cid, scale, N, main_bulk, comment))
        self.n += 1
        return self.n

    @Load.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)
        #: Set identification number
        load_id = np.zeros(ncards, dtype='int32')
        #: Coordinate system identification number.
        coord_id = np.zeros(ncards, dtype='int32')
        #: scale factor
        scale = np.zeros(ncards, dtype='float64')

        #: Indicates whether the CID coordinate system is defined in the
        #: main Bulk Data Section (MB = -1) or the partitioned superelement
        #: Bulk Data Section (MB = 0). Coordinate systems referenced in the
        #: main Bulk Data Section are considered stationary with respect to
        #: the assembly basic coordinate system. See Remark 10.
        #: (Integer; Default = 0)
        main_bulk = np.zeros(ncards, dtype='int32')

        #: Acceleration vector components measured in coordinate system CID
        N = np.zeros((ncards, 3), dtype='float64')

        assert ncards > 0, ncards
        for icard, card in enumerate(self.cards):
            (sid, cid, scalei, Ni, main_bulki, comment) = card
            load_id[icard] = sid
            coord_id[icard] = cid
            scale[icard] = scalei
            main_bulk[icard] = main_bulki
            N[icard, :] = Ni
        self._save(load_id, coord_id, scale, main_bulk, N)
        assert len(self.load_id) == self.n
        self.cards = []

    def _save(self, load_id, coord_id, scale, main_bulk, N):
        if len(self.load_id):
            load_id = np.hstack([self.load_id, load_id])
            coord_id = np.hstack([self.coord_id, coord_id])
            scale = np.hstack([self.scale, scale])
            main_bulk = np.hstack([self.main_bulk, main_bulk])
            N = np.vstack([self.N, N])
        nloads = len(load_id)
        self.load_id = load_id
        self.coord_id = coord_id
        self.scale = scale
        self.main_bulk = main_bulk
        self.N = N
        self.n = nloads

    def geom_check(self, missing: dict[str, np.ndarray]):
        cid = self.model.coord.coord_id
        geom_check(self,
                   missing,
                   coord=(cid, self.coord_id))

    @parse_load_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        print_card = get_print_card_8_16(size)
        #array_str, array_default_int
        load_ids = array_default_int(self.load_id, size=size)
        coord_ids = array_default_int(self.coord_id, default=0, size=size)
        main_bulks = array_default_int(self.main_bulk, default=0, size=size)
        for sid, cid, scale, main_bulk, N in zip(load_ids, coord_ids, self.scale, main_bulks, self.N):
            #cids = set_string8_blank_if_default(cid, 0)
            list_fields = ['GRAV', sid, cid, scale, N[0], N[1], N[2], main_bulk]
            #msg = 'GRAV    %8d%8d%8s%8s%8s%8s%8s\n' % (
                #sid, nid,
                #cids, print_float_8(mag), print_float_8(xyz[0]),
                #print_float_8(xyz[1]), print_float_8(xyz[2]))
            bdf_file.write(print_card(list_fields))
        return


class ACCEL(Load):
    """
    Acceleration Load

    Defines static acceleration loads, which may vary over a region of
    the structural model. The load variation is based upon the tabular
    input defined on this Bulk Data entry.

    +-------+------+------+--------+------+-----+-----+--------+-----+
    |   1   |   2  |   3  |    4   |   5  |  6  |  7  |   8    |  9  |
    +=======+======+======+========+======+=====+=====+========+=====+
    | ACCEL | SID  | CID  |   N1   |  N2  | N3  | DIR |        |     |
    +-------+------+------+--------+------+-----+-----+--------+-----+
    |       | LOC1 | VAL1 |  LOC2  | VAL2 | Continues in Groups of 2 |
    +-------+------+------+--------+------+--------------------------+
    | ACCEL |  100 |   2  |   0.0  |  1.0 | 2.0 |  X  |        |     |
    +-------+------+------+--------+------+-----+-----+--------+-----+
    |       |  1.0 |  1.1 |   2.0  |  2.1 | 3.0 | 3.1 |  4.0   | 4.1 |
    +-------+------+------+--------+------+-----+-----+--------+-----+

    """
    def slice_card_by_index(self, i: np.ndarray) -> ACCEL:
        load = ACCEL(self.model)
        self.__apply_slice__(load, i)
        return load

    def __apply_slice__(self, load: ACCEL, i: np.ndarray) -> None:
        load.n = len(i)
        load.load_id = self.load_id[i]
        load.locs = hslice_by_idim(i, self.iloc, self.locs)
        load.vals = hslice_by_idim(i, self.iloc, self.vals)
        load.nloc = self.nloc[i]
        load.coord_id = self.coord_id[i]
        load.direction = self.direction[i]
        load.N = self.N[i, :]

    def add(self, sid: int, N: list[float], direction: str,
            locs: list[float], vals: list[float], cid: int=0,
            comment: str='') -> int:
        """
        Creates an ACCEL card

        Parameters
        ----------
        sid : int
            load id
        N : (3, ) float ndarray
            the acceleration vector in the cid frame
        direction : str
            Component direction of acceleration variation
            {X, Y, Z}
        locs : list[float]
            Location along direction DIR in coordinate system CID for
            specification of a load scale factor.
        vals : list[float]
            The load scale factor associated with location LOCi
        cid : int; default=0
            the coordinate system for the load
        comment : str; default=''
            a comment for the card

        """
        self.cards.append((sid, N, direction, locs, vals, cid, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        """
        Adds a ACCEL card from ``BDF.add_card(...)``

        Parameters
        ----------
        card : BDFCard()
            a BDFCard object
        comment : str; default=''
            a comment for the card

        """
        sid = integer(card, 1, 'sid')
        cid = integer_or_blank(card, 2, 'cid', default=0)
        N = [double_or_blank(card, 3, 'N1', default=0.0),
             double_or_blank(card, 4, 'N2', default=0.0),
             double_or_blank(card, 5, 'N3', default=0.0)]
        direction = string(card, 6, 'dir')

        i = 9
        locs = []
        vals = []
        j = 0
        nfields = len(card)
        while i < nfields:
            #raise NotImplementedError('ACCEL-line 2')
            loc = double(card, i, 'loc%d' % j)
            val = double(card, i, 'val%d' % j)
            #print('i=%s j=%s len=%s loc=%s val=%s' % (i, j, len(card), loc, val))
            locs.append(loc)
            vals.append(val)
            j += 1
            i += 2
        #return ACCEL(sid, N, direction, locs, vals, cid=cid, comment=comment)
        self.cards.append((sid, N, direction, locs, vals, cid, comment))
        self.n += 1
        return self.n

    @VectorizedBaseCard.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)

        #: Set identification number
        load_id = np.zeros(ncards, dtype='int32')
        #: Coordinate system identification number.
        coord_id = np.zeros(ncards, dtype='int32')

        nloc = np.zeros(ncards, dtype='int32')

        #: Acceleration vector components measured in coordinate system CID
        N = np.zeros((ncards, 3), dtype='float64')
        direction = np.zeros(ncards, dtype='|U1')

        assert ncards > 0, ncards
        locs = []
        vals = []
        for icard, card in enumerate(self.cards):
            (sid, Ni, directioni, locsi, valsi, cid, comment) = card
            assert len(locsi) == len(valsi)
            load_id[icard] = sid
            coord_id[icard] = cid
            nloci = len(locsi)
            nloc[icard] = nloci
            locs.extend(locsi)
            vals.extend(valsi)
            direction[icard] = directioni
            N[icard, :] = Ni
        locs = np.array(locs, dtype='float64')
        vals = np.array(vals, dtype='float64')
        self._save(load_id, coord_id, nloc, locs, vals, direction, N)
        assert len(self.load_id) == self.n
        self.cards = []

    def _save(self, load_id, coord_id, nloc, locs, vals, direction, N):
        if len(self.load_id) != 0:
            asdf
        nloads = len(load_id)
        self.load_id = load_id
        self.coord_id = coord_id
        self.nloc = nloc
        self.locs = locs
        self.vals = vals
        self.direction = direction
        self.N = N
        self.n = nloads

    @property
    def iloc(self) -> np.ndarray:
        return make_idim(self.n, self.nloc)

    @parse_load_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        print_card = get_print_card_8_16(size)

        load_ids = array_default_int(self.load_id, size=size)
        coord_ids = array_default_int(self.coord_id, default=0, size=size)
        for sid, cid, (iloc0, iloc1), N, directioni in zip(load_ids, coord_ids, self.iloc, self.N, self.direction):
            locs = self.locs[iloc0:iloc1]
            vals = self.vals[iloc0:iloc1]

            list_fields = [
                'ACCEL', sid, cid, N[0], N[1], N[2], directioni, None, None,
            ]
            for loc, val in zip(locs, vals):
                list_fields += [loc, val]
            bdf_file.write(print_card(list_fields))
        return


class ACCEL1(Load):
    def slice_card_by_index(self, i: np.ndarray) -> ACCEL1:
        load = ACCEL1(self.model)
        self.__apply_slice__(load, i)
        return load

    def __apply_slice__(self, load: ACCEL1, i: np.ndarray) -> None:
        load.n = len(i)
        load.load_id = self.load_id[i]
        load.nodes = hslice_by_idim(i, self.inode, self.nodes)
        load.nnodes = self.nnodes[i]
        load.coord_id = self.coord_id[i]
        load.scale = self.scale[i]
        load.N = self.N[i, :]

    def add(self, sid: int, scale: float,
            N: list[float], nodes: list[int],
            cid: int=0, comment: str='') -> int:
        """
        Creates an ACCEL1 card

        Parameters
        ----------
        sid : int
            load id
        scale : float
            scale factor for load
        N : (3, ) float ndarray
            the acceleration vector in the cid frame
        nodes : list[int]
            the nodes to apply acceleration to
        cid : int; default=0
            the coordinate system for the load
        comment : str; default=''
            a comment for the card

        """
        self.cards.append((sid, scale, N, nodes, cid, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        """
        Adds a ACCEL1 card from ``BDF.add_card(...)``

        Parameters
        ----------
        card : BDFCard()
            a BDFCard object
        comment : str; default=''
            a comment for the card

        """
        sid = integer(card, 1, 'sid')
        cid = integer_or_blank(card, 2, 'cid', default=0)
        scale = double(card, 3, 'scale')
        N = [double_or_blank(card, 4, 'N1', default=0.0),
             double_or_blank(card, 5, 'N2', default=0.0),
             double_or_blank(card, 6, 'N3', default=0.0)]

        nodes = fields(integer_or_string, card, 'node', i=9, j=len(card))
        #return ACCEL1(sid, scale, N, nodes, cid=cid, comment=comment)
        self.cards.append((sid, scale, N, nodes, cid, comment))
        self.n += 1
        return self.n

    @VectorizedBaseCard.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)

        #: Set identification number
        load_id = np.zeros(ncards, dtype='int32')
        #: Coordinate system identification number.
        coord_id = np.zeros(ncards, dtype='int32')

        nnodes = np.zeros(ncards, dtype='int32')

        #: Acceleration vector components measured in coordinate system CID
        N = np.zeros((ncards, 3), dtype='float64')
        scale = np.zeros(ncards, dtype='float64')
        #direction = np.zeros(ncards, dtype='|U1')

        assert ncards > 0, ncards
        nodes = []
        for icard, card in enumerate(self.cards):
            (sid, scalei, Ni, nodesi, cidi, comment) = card
            #print(Ni, directioni, locsi, valsi)
            nodesi2 = expand_thru_by(nodesi)
            load_id[icard] = sid
            coord_id[icard] = cidi
            scale[icard] = scalei
            nnodes[icard] = len(nodesi2)
            nodes.extend(nodesi2)
            N[icard, :] = Ni
        #assert isinstance(nnodes.tolist()[0], int), nnodes[0]

        nodes = np.array(nodes, dtype='int32')
        self._save(load_id, coord_id, scale, nnodes, nodes, N)
        assert len(self.load_id) == self.n
        self.cards = []

    def _save(self, load_id, coord_id, scale, nnodes, nodes, N):
        if len(self.load_id) != 0:
            asdf
        nloads = len(load_id)
        self.load_id = load_id
        self.coord_id = coord_id
        self.nnodes = nnodes
        #assert isinstance(self.nnodes.tolist()[0], int), self.nnodes[0]
        self.nodes = nodes
        self.scale = scale
        self.N = N
        self.n = nloads

    @property
    def inode(self) -> np.ndarray:
        assert isinstance(self.nnodes.tolist()[0], int), self.nnodes[0]
        return make_idim(self.n, self.nnodes)

    @parse_load_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        print_card = get_print_card_8_16(size)

        load_ids = array_default_int(self.load_id, size=size)
        coord_ids = array_default_int(self.coord_id, default=0, size=size)
        for sid, cid, scale, (inode0, inode1), N in zip(load_ids, coord_ids, self.scale, self.inode, self.N):
            nodes = self.nodes[inode0:inode1]
            #print(N, nodes)

            list_fields = [
                'ACCEL1', sid, cid, scale, N[0], N[1], N[2], None, None
            ] + collapse_thru_by(nodes)
            bdf_file.write(print_card(list_fields))
        return


class LOAD(Load):
    """
    +------+-----+------+------+----+-----+----+----+----+
    |   1  |  2  |  3   |  4   | 5  |  6  | 7  | 8  | 9  |
    +======+=====+======+======+====+=====+====+====+====+
    | LOAD | SID |  S   |  S1  | L1 | S2  | L2 | S3 | L3 |
    +------+-----+------+------+----+-----+----+----+----+
    |      | S4  |  L4  | etc. |    |     |    |    |    |
    +------+-----+------+------+----+-----+----+----+----+
    | LOAD | 101 | -0.5 | 1.0  | 3  | 6.2 | 4  |    |    |
    +------+-----+------+------+----+-----+----+----+----+

    """
    def __init__(self, model: BDF):
        super().__init__(model)
        self.nloads = np.array([], dtype='int32')
        self.load_ids = np.array([], dtype='int32')
        self.scale_factors = np.array([], dtype='float64')

    def add(self, sid: int, scale: float,
            scale_factors: list[float],
            load_ids: list[int], comment: str='') -> int:
        assert len(scale_factors) == len(load_ids), f'sid={sid:d} scale_factors={scale_factors} load_ids={load_ids}'
        self.cards.append((sid, scale, scale_factors, load_ids, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        sid = integer(card, 1, 'sid')
        scale = double(card, 2, 'scale')

        scale_factors = []
        load_ids = []

        # alternating of scale factor & load set ID
        nload_fields = len(card) - 3
        assert nload_fields % 2 == 0, 'card=%s' % card
        for iload in range(nload_fields // 2):
            n = 2 * iload + 3
            scale_factors.append(double(card, n, 'scale_factor'))
            load_ids.append(integer(card, n + 1, 'load_id'))

        assert len(card) > 3, 'len(%s card) = %i\ncard=%s' % (self.type, len(card), card)
        self.cards.append((sid, scale, scale_factors, load_ids, comment))
        self.n += 1
        return self.n

    @VectorizedBaseCard.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)
        load_id = np.zeros(ncards, dtype='int32')
        scale = np.zeros(ncards, dtype='float64')
        nloads = np.zeros(ncards, dtype='int32')

        all_load_ids = []
        all_scale_factors = []
        assert ncards > 0, ncards
        for icard, card in enumerate(self.cards):
            (sid, scalei, scale_factors, load_ids, comment) = card

            nloads_actual = len(scale_factors)

            load_id[icard] = sid
            scale[icard] = scalei
            nloads[icard] = nloads_actual
            all_load_ids.extend(load_ids)
            all_scale_factors.extend(scale_factors)
        load_ids = np.array(all_load_ids, dtype='int32')
        scale_factors = np.array(all_scale_factors, dtype='float64')
        self._save(load_id, scale, nloads, load_ids, scale_factors)
        self.cards = []

    def _save(self, load_id, scale, nloads, load_ids, scale_factors):
        if len(self.load_id) != 0:
            load_id = np.hstack([self.load_id, load_id])
            scale = np.hstack([self.scale, scale])
            nloads = np.hstack([self.nloads, nloads])
            load_ids = np.hstack([self.load_ids, load_ids])
            scale_factors = np.hstack([self.scale_factors, scale_factors])
        self.load_id = load_id
        self.scale = scale
        self.nloads = nloads
        self.load_ids = load_ids
        self.scale_factors = scale_factors

    def __apply_slice__(self, load: LOAD, i: np.ndarray) -> None:  # ignore[override]
        load.n = len(i)
        load.load_id = self.load_id[i]
        load.scale = self.scale[i]

        iload = self.iload
        load.load_ids = hslice_by_idim(i, iload, self.load_ids)
        load.scale_factors = hslice_by_idim(i, iload, self.scale_factors)
        load.nloads = self.nloads[i]

    @property
    def iload(self) -> np.ndarray:
        return make_idim(self.n, self.nloads)

    @parse_load_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        #get_reduced_loads(self, filter_zero_scale_factors=False)
        print_card = get_print_card_8_16(size)

        for sid, scale, iload in zip(self.load_id, self.scale, self.iload):
            iload0, iload1 = iload
            list_fields = ['LOAD', sid, scale]
            scale_factors = self.scale_factors[iload0:iload1]
            load_ids = self.load_ids[iload0:iload1]
            for (scale_factor, load_id) in zip(scale_factors, load_ids):
                list_fields += [scale_factor, load_id]
            #if len(load_ids) != len(scale_factors):
                #msg = 'nload_ids=%s nscale_factors=%s and arent the same\n' % (
                    #len(load_ids), len(scale_factors))
                #msg = 'load_ids=%s\n' % (load_ids)
                #msg += 'scale_factors=%s\n' % (scale_factors)
                #msg += print_card_8(list_fields)
                #msg += str(self.get_stats())
                #raise IndexError(msg)
            bdf_file.write(print_card(list_fields))
        #else:
            #raise RuntimeError(size)
        return


    #def get_loads_by_load_id(self) -> dict[int, Loads]:
        #return get_loads_by_load_id(self)

    def get_loads_by_load_id(load: Union[LOAD, LOADSET]) -> dict[int, Loads]:
        """"""
        model = load.model
        #uload_ids = np.unique(self.load_ids)
        loads_by_load_id = defaultdict(list)

        #print('all_laods =', model.loads)
        for loadi in model.load_cards:
            if loadi.type in {'LOAD', 'LSEQ'}:
                continue
            if loadi.n == 0:
                continue
            uload_idsi = np.unique(loadi.load_id)
            #print(f'load.type={loadi.type} {uload_idsi}')
            for uload_id in uload_idsi:
                #print(loadi.load_id)
                #i = np.where(uload_id == loadi.load_id)[0]
                #if len(i) == 0:
                    #print('i =', i)
                    #jj
                    #continue
                #print(f'load.type={loadi.type} {uload_id}; i={i}')
                #loadi = loadi.slice_card_by_index(i)
                loadi2 = loadi.slice_card_by_load_id(uload_id)
                #if loadi.type == 'PLOAD4':
                    #loadi.nvector

                loads_by_load_id[uload_id].append(loadi2)

        #loads_by_load_id = dict(loads_by_load_id)

        #load = model.load
        #for sid, scale, iload in zip(load.load_id, load.scale, load.iload):
            #iload0, iload1 = iload
            ##list_fields = ['LOAD', sid, scale]
            #scale_factors = load.scale_factors[iload0:iload1]
            #load_ids = load.load_ids[iload0:iload1]
            #for (scale_factor, load_id) in zip(scale_factors, load_ids):
                #scale2 = scale * scale_factor
                #cards = loads_by_load_id[load_id]
                #loads_by_load_id[uload_id].append(loadi2)

                #list_fields += [scale_factor, load_id]
        return dict(loads_by_load_id)

    def get_reduced_loads(self,
                          remove_missing_loads: bool=False,
                          filter_zero_scale_factors: bool=False,
                          stop_on_failure: bool=True) -> dict[int, Loads]:
        return get_reduced_loads(
            self, remove_missing_loads=remove_missing_loads,
            filter_zero_scale_factors=filter_zero_scale_factors,
            stop_on_failure=stop_on_failure)

    def get_reduced_load_by_load_id(self,
                                    load_id: int,
                                    remove_missing_loads: bool=False,
                                    filter_zero_scale_factors: bool=False,
                                    stop_on_failure: bool=True) -> dict[int, Loads]:
        """
        Parameters
        ----------
        resolve_load_card : bool; default=False
            ???
        remove_missing_loads: bool; default=False
            LOAD cards can reference loads (e.g., GRAV) that don't exist
            Nastran sometimes ignores these loads leading to potentially incorrect results
        filter_zero_scale_factors: bool; default=False
            remove loads that are 0.0
        """
        load = self.slice_card_by_load_id(load_id)
        reduced_loads = get_reduced_loads(load)
        return reduced_loads


def get_reduced_static_load_from_load_id(model: BDF,
                                         load_id: int,
                                         remove_missing_loads: bool=False,
                                         filter_zero_scale_factors: bool=False,
                                         stop_on_failure: bool=True) -> list[StaticLoad]:
    #log = model.log

    load: LOAD = model.load
    reduced_loads = []
    if load.n and load_id in load.load_id:
        load.get_reduced_load_by_load_id(
            load_id,
            remove_missing_loads=remove_missing_loads,
            filter_zero_scale_factors=filter_zero_scale_factors,
            stop_on_failure=stop_on_failure)
        #reduced_loads = load.get_reduced_loads(
            #remove_missing_loads=False,
            #filter_zero_scale_factors=False,
            #stop_on_failure=True)
        #raise RuntimeError('aaa')
    else:
        for load in model.load_cards:
            if load.n == 0:
                continue
            if load.type in {'LOAD', 'LSEQ'}:
                model.log.debug(f'skipping {load.type}')
                continue
            scale_factor = 1.
            loadi = load.slice_card_by_load_id(load_id)
            reduced_loads.append((scale_factor, loadi))
    return reduced_loads

def get_reduced_loads(load: Union[LOAD, LSEQ],
                      remove_missing_loads: bool=False,
                      filter_zero_scale_factors: bool=False,
                      stop_on_failure: bool=True) -> dict[int, Loads]:
    """
    Parameters
    ----------
    resolve_load_card : bool; default=False
        ???
    remove_missing_loads: bool; default=False
        LOAD cards can reference loads (e.g., GRAV) that don't exist
        Nastran sometimes ignores these loads leading to potentially incorrect results
    filter_zero_scale_factors: bool; default=False
        remove loads that are 0.0
    """
    reduced_loads = {}
    if load.n == 0:
        return reduced_loads

    stop_on_failure = True
    loads_by_load_id = load.get_loads_by_load_id()
    log = load.model.log
    for sid, global_scale, iload in zip(load.load_id, load.scale_factors, load.iload):
        reduced_loadsi = []
        iload0, iload1 = iload
        if global_scale == 0. and filter_zero_scale_factors:
            print('continueA')
            continue
        scale_factors = global_scale * load.scale_factors[iload0:iload1]
        load_ids = load.load_ids[iload0:iload1]
        for (scale_factor, load_id) in zip(scale_factors, load_ids):
            if scale_factor == 0. and filter_zero_scale_factors:
                continue

            if load_id in loads_by_load_id:
                loads_found = loads_by_load_id[load_id]
                if len(loads_found) == 0:
                    msg = f'No referenced loads found for load_id={load_id} on {load.type} load_id={sid}'
                    log.error(msg)
                    if stop_on_failure:
                        raise RuntimeError(msg)
                reduced_loadsi.append((scale_factor, loads_found))
            elif load_id in reduced_loads:
                #scale_factors = global_scale * load.scale_factors[iload0:iload1]
                log.warning(f'LOAD card sid={sid} references another LOAD sid={load_id:d}')
                #for scalei, loadi in reduced_loads[load_id]:
                    #scale_factor2 = scalei * scale_factor
                    #reduced_loadsi.append((scale_factor2, loadi))
                x = 1
            else:
                log.warning(f'cannot find load_id={load_id:d}; '
                            'does a LOAD card reference another LOAD card?')
        if len(reduced_loadsi) == 0:
            continue
        reduced_loads[sid] = reduced_loadsi

    # loads that weren't referenced by a LOAD card
    for load_id, loads in loads_by_load_id.items():
        if load_id not in reduced_loads:
            reduced_loads[load_id] = [(1., loads)]
    return reduced_loads


class SLOAD(Load):
    """
    Static Scalar Load
    Defines concentrated static loads on scalar or grid points.

    +-------+-----+----+-----+----+------+----+-------+
    |   1   |  2  | 3  |  4  |  5 |  6   |  7 |   8   |
    +=======+=====+====+=====+====+======+====+=======+
    | SLOAD | SID | S1 | F1  | S2 |  F2  | S3 |   F3  |
    +-------+-----+----+-----+----+------+----+-------+
    | SLOAD | 16  | 2  | 5.9 | 17 | -6.3 | 14 | -2.93 |
    +-------+-----+----+-----+----+------+----+-------+

    .. note:: Can be used in statics OR dynamics.

    If Si refers to a grid point, the load is applied to component T1 of the
    displacement coordinate system (see the CD field on the GRID entry).
    """
    #def slice_card_by_index(self, i: np.ndarray) -> SLOAD:
        #"""uses a node_index to extract PBARs"""
        #i = np.atleast_1d(np.asarray(i, dtype=self.load_id.dtype))
        #i.sort()
        #assert len(self.load_id) > 0, self.load_id
        #load = SLOAD(self.model)
        #self.__apply_slice__(load, i)
        #return load

    def __apply_slice__(self, load: SLOAD, i: np.ndarray) -> None:
        load.n = len(i)
        load.load_id = self.load_id[i]
        load.nodes = self.nodes
        load.mags = self.mags

    def add(self, sid: int, nodes: list[int], mags: list[float],
            comment: str='') -> int:
        """
        Creates an SLOAD (GRID/SPOINT load)

        Parameters
        ----------
        sid : int
            load id
        nids : int; list[int]
            the GRID/SPOINT ids
        mags : float; list[float]
            the load magnitude
        comment : str; default=''
            a comment for the card

        """
        if isinstance(nodes, integer_types):
            nodes = [nodes]
        if isinstance(mags, float_types):
            mags = [mags]
        assert len(nodes) == len(mags)
        self.cards.append((sid, nodes, mags, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        sid = integer(card, 1, 'sid')

        nfields = len(card) - 2
        ngroups = nfields // 2
        if nfields % 2 == 1:
            ngroups += 1
            msg = 'Missing last magnitude on SLOAD card=%s' % card.fields()
            raise RuntimeError(msg)

        nodes = []
        mags = []
        for i in range(ngroups):
            j = 2 * i + 2
            nodes.append(integer(card, j, f'nid{i:d}'))
            mags.append(double(card, j + 1, f'mag{i:d}'))
        self.cards.append((sid, nodes, mags, comment))
        self.n += 1
        return self.n

    @Load.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)
        assert ncards > 0, ncards
        all_sids = []
        all_nodes = []
        all_mags = []
        for icard, card in enumerate(self.cards):
            sid, nodesi, magsi, comment = card
            #nloadsi = len(nodesi)
            sids = [sid] * len(nodesi)
            all_sids.extend(sids)
            all_nodes.extend(nodesi)
            all_mags.extend(magsi)

        load_id = np.array(all_sids, dtype='int32')
        nodes = np.array(all_nodes, dtype='int32')
        mags = np.array(all_mags, dtype='float64')
        self._save(load_id, nodes, mags)
        self.sort()
        self.cards = []

    def _save(self, load_id, nodes, mags):
        if len(self.load_id) != 0:
            load_id = np.hstack([self.load_id, load_id])
            nodes = np.hstack([self.nodes, nodes])
            mags = np.hstack([self.mags, mags])

        nloads = len(load_id)
        self.load_id = load_id
        self.nodes = nodes
        self.mags = mags
        self.n = nloads

    def geom_check(self, missing: dict[str, np.ndarray]):
        spoint = self.model.spoint
        used_spoints = np.unique(self.nodes)
        geom_check(self,
                   missing,
                   spoint=(spoint, used_spoints), )

    def sum_forces_moments(self) -> np.ndarray:
        #spoint = self.model.spoint
        #xyz_cid0 = grid.xyz_cid0()
        #nid = spoint.spoint_id

        nloads = len(self.load_id)
        force_moment = np.zeros((nloads, 6), dtype='float64')
        force = force_moment[:, :3]
        #moment = force_moment[:, 3:]
        uload_id = np.unique(self.load_id)
        assert len(uload_id) == 1, uload_id
        force[:, 0] = self.mags
        return force_moment

    @parse_load_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        print_card = get_print_card_8_16(size)
        load_ids = array_str(self.load_id, size=size)
        for sid, node, mag in zip(load_ids, self.nodes, self.mags):
            list_fields = ['SLOAD', sid, node, mag]
            bdf_file.write(print_card(list_fields))
        return


class RFORCE(Load):
    def __init__(self, model: BDF):
        super().__init__(model)

    def slice_card_by_index(self, i: np.ndarray) -> RFORCE:
        load = RFORCE(self.model)
        self.__apply_slice__(load, i)
        return load

    def __apply_slice__(self, load: RFORCE, i: np.ndarray) -> None:
        #self.model.log.info(self.dphase_int)
        #self.model.log.info(i)
        assert len(i) > 0
        load.n = len(i)

        load.load_id = self.load_id[i]
        load.node_id = self.node_id[i]
        load.coord_id = self.coord_id[i]
        load.scale = self.scale[i]
        load.r = self.r[i, :]
        load.method = self.method[i]
        load.racc = self.racc[i]
        load.main_bulk = self.main_bulk[i]
        load.idrf = self.idrf[i]

    def add(self, sid: int, nid: int, scale: float, r123: list[float],
            cid: int=0, method: int=1, racc: float=0.,
            main_bulk: int=0, idrf: int=0, comment: str='') -> int:
        """
        idrf doesn't exist in MSC 2005r2; exists in MSC 2016

        Parameters
        ----------
        sid : int
            load set id
        nid : int
            grid point through which the rotation vector acts
        scale : float
            scale factor of the angular velocity in revolutions/time
        r123 : list[float, float, float] / (3, ) float ndarray
            rectangular components of the rotation vector R that passes
            through point G (R1**2+R2**2+R3**2 > 0 unless A and RACC are
            both zero).
        cid : int; default=0
            Coordinate system defining the components of the rotation vector.
        method : int; default=1
            Method used to compute centrifugal forces due to angular velocity.
        racc : int; default=0.0
            Scale factor of the angular acceleration in revolutions per
            unit time squared.
        main_bulk : int; default=0
            Indicates whether the CID coordinate system is defined in the main
            Bulk Data Section (MB = -1) or the partitioned superelement Bulk
            Data Section (MB = 0). Coordinate systems referenced in the main
            Bulk Data Section are considered stationary with respect to the
            assembly basic coordinate system.
        idrf : int; default=0
            ID indicating to which portion of the structure this particular
            RFORCE entry applies. It is possible to have multiple RFORCE
            entries in the same subcase for SOL 600 to represent different
            portions of the structure with different rotational accelerations.
            IDRF corresponds to a SET3 entry specifying the elements with this
            acceleration. A BRKSQL entry may also be specified with a matching
            IDRF entry.
        comment : str; default=''
            a comment for the card

        """
        self.cards.append((sid, nid, cid, scale, r123,
                           method, racc, main_bulk, idrf, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        """
        Adds a RFORCE card from ``BDF.add_card(...)``

        Parameters
        ----------
        card : BDFCard()
            a BDFCard object
        comment : str; default=''
            a comment for the card

        """
        sid = integer(card, 1, 'sid')
        nid = integer_or_blank(card, 2, 'nid', default=0)
        cid = integer_or_blank(card, 3, 'cid', default=0)
        scale = double_or_blank(card, 4, 'scale', default=1.)
        r1 = double_or_blank(card, 5, 'r1', default=0.)
        r2 = double_or_blank(card, 6, 'r2', default=0.)
        r3 = double_or_blank(card, 7, 'r3', default=0.)
        method = integer_or_blank(card, 8, 'method', default=1)
        racc = double_or_blank(card, 9, 'racc', default=0.)
        main_bulk = integer_or_blank(card, 10, 'mb', default=0)
        idrf = integer_or_blank(card, 11, 'idrf', default=0)
        assert len(card) <= 12, f'len(RFORCE card) = {len(card):d}\ncard={card}'
        self.cards.append((sid, nid, cid, scale, [r1, r2, r3],
                           method, racc, main_bulk, idrf, comment))
        self.n += 1
        return self.n

    @Load.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)

        #: Set identification number
        load_id = np.zeros(ncards, dtype='int32')

        # nid : int
        #     grid point through which the rotation vector acts
        node_id = np.zeros(ncards, dtype='int32')

        # cid : int; default=0
        #     Coordinate system defining the components of the rotation vector.
        coord_id = np.zeros(ncards, dtype='int32')

        # scale : float
        #     scale factor of the angular velocity in revolutions/time
        scale = np.zeros(ncards, dtype='float64')

        # r123 : list[float, float, float] / (3, ) float ndarray
        #     rectangular components of the rotation vector R that passes
        #     through point G (R1**2+R2**2+R3**2 > 0 unless A and RACC are
        #     both zero).
        r = np.zeros((ncards, 3), dtype='float64')

        # method : int; default=1
        #     Method used to compute centrifugal forces due to angular velocity.
        method = np.zeros(ncards, dtype='int32')

        # racc : int; default=0.0
        #     Scale factor of the angular acceleration in revolutions per
        #     unit time squared.
        racc = np.zeros(ncards, dtype='float64')

        # mb : int; default=0
        #     Indicates whether the CID coordinate system is defined in the main
        #     Bulk Data Section (MB = -1) or the partitioned superelement Bulk
        #     Data Section (MB = 0). Coordinate systems referenced in the main
        #     Bulk Data Section are considered stationary with respect to the
        #     assembly basic coordinate system.
        main_bulk = np.zeros(ncards, dtype='int32')

        # idrf : int; default=0
        #     ID indicating to which portion of the structure this particular
        #     RFORCE entry applies. It is possible to have multiple RFORCE
        #     entries in the same subcase for SOL 600 to represent different
        #     portions of the structure with different rotational accelerations.
        #     IDRF corresponds to a SET3 entry specifying the elements with this
        #     acceleration. A BRKSQL entry may also be specified with a matching
        #     IDRF entry.
        idrf = np.zeros(ncards, dtype='int32')

        assert ncards > 0, ncards
        for icard, card in enumerate(self.cards):
            (sid, nid, cid, scalei, r123, methodi, racci, mb, idrfi, comment) = card
            load_id[icard] = sid
            node_id[icard] = nid
            coord_id[icard] = cid
            scale[icard] = scalei
            r[icard, :] = r123
            method[icard] = methodi
            racc[icard] = racci
            main_bulk[icard] = mb
            idrf[icard] = idrfi

        self._save(load_id, node_id, coord_id, scale, r, method, racc, main_bulk, idrf)
        assert len(self.load_id) == self.n
        self.cards = []

    def _save(self, load_id, node_id, coord_id, scale, r, method, racc, main_bulk, idrf):
        if len(self.load_id) != 0:
            asdf
        self.load_id = load_id
        self.node_id = node_id
        self.coord_id = coord_id
        self.scale = scale
        self.r = r
        self.method = method
        self.racc = racc
        self.main_bulk = main_bulk
        self.idrf = idrf
        assert isinstance(self.r, np.ndarray), type(self.r)

    def geom_check(self, missing: dict[str, np.ndarray]):
        nid = self.model.grid.node_id
        cid = self.model.coord.coord_id

        geom_check(self,
                   missing,
                   node=(nid, self.node_id), filter_node0=False,
                   coord=(cid, self.coord_id))

    def sum_forces_moments(self) -> np.ndarray:
        self.model.log.warning("RFORCE hasn't implemented sum_forces_moments")
        force_moment = np.zeros((len(self.load_id), 6), dtype='float64')
        return force_moment

    @parse_load_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        print_card = get_print_card_8_16(size)
        #array_str, array_default_int
        load_ids = array_str(self.load_id, size=size)
        nids = array_default_int(self.node_id, default=0, size=size)
        cids = array_default_int(self.coord_id, default=0, size=size)
        methods = array_default_int(self.method, default=1, size=size)
        mbs = array_default_int(self.main_bulk, default=0, size=size)
        idrfs = array_default_int(self.idrf, default=0, size=size)
        for sid, nid, cid, scale, r123, method, racc, mb, idrf in zip_longest(
            load_ids, nids, cids, self.scale, self.r.tolist(), methods, self.racc, mbs, idrfs):
            list_fields = (['RFORCE', sid, nid, cid, scale] +
                           r123 + [method, racc, mb, idrf])
            bdf_file.write(print_card(list_fields))
        return


class RFORCE1(Load):
    """
    NX Nastran specific card

    +---------+------+----+---------+---+----+----+----+--------+
    |    1    |   2  | 3  |    4    | 5 |  6 |  7 |  8 |   9    |
    +=========+======+====+=========+===+====+====+====+========+
    | RFORCE1 | SID  | G  |   CID   | A | R1 | R2 | R3 | METHOD |
    +---------+------+----+---------+---+----+----+----+--------+
    |         | RACC | MB | GROUPID |   |    |    |    |        |
    +---------+------+----+---------+---+----+----+----+--------+
    """
    def __init__(self, model: BDF):
        super().__init__(model)

    def slice_card_by_index(self, i: np.ndarray) -> RFORCE1:
        load = RFORCE1(self.model)
        self.__apply_slice__(load, i)
        return load

    def __apply_slice__(self, load: RFORCE1, i: np.ndarray) -> None:
        #self.model.log.info(self.dphase_int)
        #self.model.log.info(i)
        assert len(i) > 0
        load.n = len(i)

        load.load_id = self.load_id[i]
        load.node_id = self.node_id[i]
        load.coord_id = self.coord_id[i]
        load.scale = self.scale[i]
        load.r = self.r[i, :]
        load.method = self.method[i]
        load.racc = self.racc[i]
        load.main_bulk = self.main_bulk[i]
        load.group_id = self.group_id[i]

    def add(self, sid: int, nid: int, scale: float,
            group_id: int, cid: int=0, r123: Optional[list[float]]=None,
            racc: float=0., main_bulk: int=0, method: int=2,
            comment: str='') -> int:
        """
        Creates an RFORCE1 card

        Parameters
        ----------
        sid : int
            load set id
        nid : int
            grid point through which the rotation vector acts
        scale : float
            scale factor of the angular velocity in revolutions/time
        r123 : list[float, float, float] / (3, ) float ndarray
            rectangular components of the rotation vector R that passes
            through point G
        racc : int; default=0.0
            ???
        main_bulk : int; default=0
            Indicates whether the CID coordinate system is defined in the main
            Bulk Data Section (MB = -1) or the partitioned superelement Bulk
            Data Section (MB = 0). Coordinate systems referenced in the main
            Bulk Data Section are considered stationary with respect to the
            assembly basic coordinate system.
        group_id : int
            Group identification number. The GROUP entry referenced in the
            GROUPID field selects the grid points to which the load is applied.
        cid : int; default=0
            Coordinate system defining the components of the rotation vector.
        method : int; default=2
            Method used to compute centrifugal forces due to angular velocity.
        comment : str; default=''
            a comment for the card

        """
        self.cards.append((sid, nid, cid, scale, r123,
                           method, racc, main_bulk, group_id, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        """
        Adds a RFORCE1 card from ``BDF.add_card(...)``

        Parameters
        ----------
        card : BDFCard()
            a BDFCard object
        comment : str; default=''
            a comment for the card

        """
        sid = integer(card, 1, 'sid')
        nid = integer_or_blank(card, 2, 'nid', default=0)
        cid = integer_or_blank(card, 3, 'cid', default=0)
        scale = double_or_blank(card, 4, 'scale', default=1.)
        r123 = [
            double_or_blank(card, 5, 'r1', default=1.),
            double_or_blank(card, 6, 'r2', default=0.),
            double_or_blank(card, 7, 'r3', default=0.),
        ]
        method = integer_or_blank(card, 8, 'method', default=1)
        racc = double_or_blank(card, 9, 'racc', default=0.)
        main_bulk = integer_or_blank(card, 10, 'main_bulk', default=0)
        group_id = integer_or_blank(card, 11, 'group_id', default=0)
        assert len(card) <= 12, f'len(RFORCE1 card) = {len(card):d}\ncard={card}'
        self.cards.append((sid, nid, cid, scale, r123, method, racc, main_bulk, group_id, comment))
        self.n += 1
        return self.n

    @Load.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)

        #: Set identification number
        load_id = np.zeros(ncards, dtype='int32')

        # nid : int
        #     grid point through which the rotation vector acts
        node_id = np.zeros(ncards, dtype='int32')

        # cid : int; default=0
        #     Coordinate system defining the components of the rotation vector.
        coord_id = np.zeros(ncards, dtype='int32')

        # scale : float
        #     scale factor of the angular velocity in revolutions/time
        scale = np.zeros(ncards, dtype='float64')

        # r123 : list[float, float, float] / (3, ) float ndarray
        #     rectangular components of the rotation vector R that passes
        #     through point G (R1**2+R2**2+R3**2 > 0 unless A and RACC are
        #     both zero).
        r = np.zeros((ncards, 3), dtype='float64')

        # method : int; default=1
        #     Method used to compute centrifugal forces due to angular velocity.
        method = np.zeros(ncards, dtype='int32')

        # racc : int; default=0.0
        #     Scale factor of the angular acceleration in revolutions per
        #     unit time squared.
        racc = np.zeros(ncards, dtype='float64')

        # mb : int; default=0
        #     Indicates whether the CID coordinate system is defined in the main
        #     Bulk Data Section (MB = -1) or the partitioned superelement Bulk
        #     Data Section (MB = 0). Coordinate systems referenced in the main
        #     Bulk Data Section are considered stationary with respect to the
        #     assembly basic coordinate system.
        main_bulk = np.zeros(ncards, dtype='int32')

        # Group identification number. The GROUP entry referenced in the
        # GROUPID field selects the grid points to which the load is applied.
        group_id = np.zeros(ncards, dtype='int32')

        assert ncards > 0, ncards
        for icard, card in enumerate(self.cards):
            (sid, nid, cid, scalei, r123, methodi, racci, main_bulki, group_idi, comment) = card
            load_id[icard] = sid
            node_id[icard] = nid
            coord_id[icard] = cid
            scale[icard] = scalei
            r[icard, :] = r123
            method[icard] = methodi
            racc[icard] = racci
            main_bulk[icard] = main_bulki
            group_id[icard] = group_idi
        self._save(load_id, node_id, coord_id, scale, r, method, racc, main_bulk, group_id)
        assert len(self.load_id) == self.n
        self.cards = []

    def _save(self, load_id, node_id, coord_id, scale, r,
              method, racc, main_bulk, group_id):
        if len(self.load_id) != 0:
            load_id = np.hstack([self.load_id, load_id])
            node_id = np.hstack([self.node_id, node_id])
            coord_id = np.hstack([self.coord_id, coord_id])
            r = np.vstack([self.r, r])
            method = np.hstack([self.method, method])
            racc = np.hstack([self.racc, racc])
            main_bulk = np.hstack([self.main_bulk, main_bulk])
            group_id = np.hstack([self.group_id, group_id])

        self.load_id = load_id
        self.node_id = node_id
        self.coord_id = coord_id
        self.scale = scale
        self.r = r
        self.method = method
        self.racc = racc
        self.main_bulk = main_bulk
        self.group_id = group_id

    def geom_check(self, missing: dict[str, np.ndarray]) -> None:
        nid = self.model.grid.node_id
        cid = self.model.coord.coord_id

        geom_check(self,
                   missing,
                   node=(nid, self.node_id), filter_node0=False,
                   coord=(cid, self.coord_id))

    def sum_forces_moments(self) -> np.ndarray:
        self.model.log.warning("RFORCE1 hasn't implemented sum_forces_moments")
        force_moment = np.zeros((len(self.load_id), 6), dtype='float64')
        return force_moment

    def geom_check(self, missing: dict[str, np.ndarray]):
        nid = self.model.grid.node_id
        cid = self.model.coord.coord_id

        geom_check(self,
                   missing,
                   node=(nid, self.node_id), filter_node0=False,
                   coord=(cid, self.coord_id))

    @parse_load_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        print_card = get_print_card_8_16(size)

        load_ids = array_str(self.load_id, size=size)
        nids = array_default_int(self.node_id, default=0, size=size)
        cids = array_default_int(self.coord_id, default=0, size=size)
        methods = array_default_int(self.method, default=1, size=size)
        mbs = array_default_int(self.main_bulk, default=0, size=size)
        r123s = array_float(self.r, size=size, is_double=is_double).tolist()
        group_ids = array_default_int(self.group_id, default=0, size=size)
        for sid, nid, cid, scale, r123, method, racc, mb, group_id in zip_longest(
            load_ids, nids, cids, self.scale, r123s, methods, self.racc, mbs, group_ids):
            list_fields = (['RFORCE1', sid, nid, cid, scale]
                           + r123 + [method, racc, mb, group_id])
            bdf_file.write(print_card(list_fields))
        return
