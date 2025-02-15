from __future__ import annotations
#from itertools import count
from typing import TYPE_CHECKING
import numpy as np
#from pyNastran.bdf.field_writer_8 import print_card_8 # , print_float_8, print_field_8
#from pyNastran.bdf.field_writer_16 import print_card_16, print_scientific_16, print_field_16
#from pyNastran.bdf.field_writer_double import print_scientific_double
from pyNastran.bdf.bdf_interface.assign_type import (
    integer,
    #double,
    integer_or_blank,
    #double_or_blank,
)
#from pyNastran.bdf.cards.elements.bars import set_blank_if_default
#from pyNastran.bdf.cards.properties.bars import _bar_areaL # PBARL as pbarl, A_I1_I2_I12

from pyNastran.dev.bdf_vectorized3.cards.base_card import (
    Element, parse_element_check, # searchsorted_filter,
    get_print_card_8_16)
from .rod import line_length, line_centroid
from pyNastran.dev.bdf_vectorized3.cards.write_utils import array_str #, array_default_int
from pyNastran.dev.bdf_vectorized3.bdf_interface.geom_check import geom_check
#from pyNastran.dev.bdf_vectorized3.utils import hstack_msg

if TYPE_CHECKING:
    from pyNastran.bdf.bdf_interface.bdf_card import BDFCard
    #from pyNastran.dev.bdf_vectorized3.bdf import BDF
    from pyNastran.dev.bdf_vectorized3.types import TextIOLike


class PLOTEL(Element):
    """
    Defines a 1D dummy element used for plotting.

    This element is not used in the model during any of the solution
    phases of a problem. It is used to simplify plotting of
    structures with large numbers of colinear grid points, where the
    plotting of each grid point along with the elements connecting
    them would result in a confusing plot.

    +--------+-----+-----+-----+
    |   1    |  2  |  3  |  4  |
    +========+=====+=====+=====+
    | PLOTEL | EID | G1  | G2  |
    +--------+-----+-----+-----+

    """
    def add(self, eid: int, nodes: list[int], comment: str='') -> int:
        """
        Adds a PLOTEL card

        Parameters
        ----------
        eid : int
            Element ID
        nodes : list[int, int]
            Unique GRID point IDs
        comment : str; default=''
            a comment for the card

        """
        self.cards.append((eid, nodes, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        """adds a PLOTEL"""
        #['PLOTEL', '3101', '3101', '3102', None, '3102', '3102', '3103']
        eid = integer(card, 1, 'eid')
        nodes = [
            integer(card, 2, 'g1'),
            integer(card, 3, 'g2'),
        ]
        #assert len(card) <= 4, f'len(PLOTEL card) = {len(card):d}\ncard={card}'
        self.cards.append((eid, nodes, comment))
        self.n += 1

        # TODO: find source that it's 4 and not 5
        if card.field(5):  # eid
            eid = integer(card, 5, 'eid')
            nodes = [
                integer(card, 6, 'g1'),
                integer(card, 7, 'g2'),
            ]
            self.cards.append((eid, nodes, ''))
            self.n += 1
            assert len(card) <= 8, f'len(PLOTEL card) = {len(card):d}\ncard={card}'
        else:
            assert len(card) <= 5, f'len(PLOTEL card) = {len(card):d}\ncard={card}'
        self.n += 1

    @Element.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)
        idtype = self.model.idtype
        element_id = np.zeros(ncards, dtype=idtype)
        nodes = np.zeros((ncards, 2), dtype=idtype)

        for icard, card_comment in enumerate(self.cards):
            eid, nodesi, comment = card_comment
            element_id[icard] = eid
            nodes[icard, :] = nodesi
        self._save(element_id, nodes)
        self.cards = []

    def _save(self, element_id, nodes):
        nelements = len(element_id)
        self.element_id = element_id
        self.nodes = nodes
        self.n = nelements

    def geom_check(self, missing: dict[str, np.ndarray]):
        nid = self.model.grid.node_id
        geom_check(self,
                   missing,
                   node=(nid, self.nodes))

    @parse_element_check
    def write_file(self, bdf_file: TextIOLike, size: int=8,
                   is_double: bool=False,
                   write_card_header: bool=False) -> None:
        print_card = get_print_card_8_16(size)

        element_id = array_str(self.element_id, size=size)
        nodes = array_str(self.nodes, size=size)

        for eid, nodesi in zip(element_id, nodes):
            n1, n2 = nodesi
            list_fields = ['PLOTEL', eid, n1, n2]
            bdf_file.write(print_card(list_fields))
        return

    #@property
    #def allowed_properties(self):
        #return [prop for prop in [self.model.prod]
                #if prop.n > 0]

    #def mass(self) -> np.ndarray:
        #mass_per_length = line_pid_mass_per_length(self.property_id, self.allowed_properties)
        #length = self.length()
        #mass = mass_per_length * length
        #return mass

    #def area(self) -> np.ndarray:
        #area = line_pid_area(self.property_id, self.allowed_properties)
        #return area

    def length(self) -> np.ndarray:
        length = line_length(self.model, self.nodes)
        return length

    def centroid(self) -> np.ndarray:
        centroid = line_centroid(self.model, self.nodes)
        return centroid
