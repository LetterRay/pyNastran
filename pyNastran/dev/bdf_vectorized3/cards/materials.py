from __future__ import annotations
from itertools import zip_longest
from typing import Optional, TYPE_CHECKING
import numpy as np
#from pyNastran.bdf.field_writer_8 import print_card_8 # , print_float_8, print_field_8
#from pyNastran.bdf.field_writer_16 import print_card_16, print_scientific_16, print_field_16
#from pyNastran.bdf.field_writer_double import print_scientific_double
from pyNastran.bdf.bdf_interface.assign_type import (
    integer, double, integer_or_blank, double_or_blank, # string_or_blank,
)
from pyNastran.bdf.cards.materials import mat1_E_G_nu, get_G_default, set_blank_if_default

from pyNastran.dev.bdf_vectorized3.cards.base_card import Material, get_print_card_8_16, parse_material_check
from pyNastran.dev.bdf_vectorized3.cards.write_utils import get_print_card, array_str # , array_default_int

if TYPE_CHECKING:  # pragma: no cover
    from pyNastran.bdf.bdf_interface.bdf_card import BDFCard
    from pyNastran.dev.bdf_vectorized3.bdf import BDF
    from pyNastran.dev.bdf_vectorized3.types import TextIOLike


class MAT1(Material):
    """
    Defines the material properties for linear isotropic materials.

    +------+-----+-----+-----+-------+-----+------+------+-----+
    |   1  |  2  | 3   | 4   |   5   |  6  |  7   |  8   |  9  |
    +======+=====+=====+=====+=======+=====+======+======+=====+
    | MAT1 | MID |  E  |  G  |  NU   | RHO |  A   | TREF | GE  |
    +------+-----+-----+-----+-------+-----+------+------+-----+
    |      | ST  | SC  | SS  | MCSID |     |      |      |     |
    +------+-----+-----+-----+-------+-----+------+------+-----+

    """
    def __init__(self, model: BDF):
        super().__init__(model)
        self.cards = []
        self.n = 0
        self.material_id = np.array([], dtype='int32')
        self.E = np.array([], dtype='float64')
        self.G = np.array([], dtype='float64')
        self.nu = np.array([], dtype='float64')
        self.rho = np.array([], dtype='float64')
        self.alpha = np.array([], dtype='float64')
        self.tref = np.array([], dtype='float64')
        self.ge = np.array([], dtype='float64')
        self.St = np.array([], dtype='float64')
        self.Sc = np.array([], dtype='float64')
        self.Ss = np.array([], dtype='float64')
        self.mcsid = np.array([], dtype='int32')

    def add(self, mid: int, E: float, G: float, nu: float,
            rho: float=0.0, alpha: float=0.0, tref: float=0.0, ge: float=0.0,
            St: float=0.0, Sc: float=0.0, Ss: float=0.0,
            mcsid: int=0, comment: str='') -> int:
        """
        Creates a MAT1 card

        Parameters
        ----------
        mid : int
            material id
        E : float / None
            Young's modulus
        G : float / None
            Shear modulus
        nu : float / None
            Poisson's ratio
        rho : float; default=0.
            density
        alpha : float; default=0.
            coefficient of thermal expansion
        tref : float; default=0.
            reference temperature
        ge : float; default=0.
            damping coefficient
        St / Sc / Ss : float; default=0.
            tensile / compression / shear allowable
        mcsid : int; default=0
            material coordinate system id
            used by PARAM,CURV
        comment : str; default=''
            a comment for the card

        If E, G, or nu is None (only 1), it will be calculated

        """
        E, G, nu = mat1_E_G_nu(E, G, nu)

        self.cards.append((mid, E, G, nu, rho, alpha, tref, ge, St, Sc, Ss,
                           mcsid, comment))
        self.n += 1
        #self.material_id = np.hstack([self.material_id, [mid]])
        #self.E = np.hstack([self.E, [E]])
        #self.G = np.hstack([self.G, [G]])
        #self.nu = np.hstack([self.nu, [nu]])
        #self.rho = np.hstack([self.rho, [rho]])
        #self.alpha = np.hstack([self.alpha, [alpha]])
        #self.tref = np.hstack([self.tref, [tref]])
        #self.St = np.hstack([self.St, [St]])
        #self.Sc = np.hstack([self.Sc, [Sc]])
        #self.Ss = np.hstack([self.Ss, [Ss]])
        #self.mcsid = np.hstack([self.mcsid, [mcsid]])
        #self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        mid = integer(card, 1, 'mid')
        E = double_or_blank(card, 2, 'E')
        G = double_or_blank(card, 3, 'G')
        nu = double_or_blank(card, 4, 'nu')
        if E is None and G is None and nu is None:
            E = G = nu = 0.
            self.model.log.warning(f'MAT1; mid={mid} E=G=nu=0.')
        else:
            E, G, nu = mat1_E_G_nu(E, G, nu)

        rho = double_or_blank(card, 5, 'rho', default=0.)
        alpha = double_or_blank(card, 6, 'a', default=0.0)
        tref = double_or_blank(card, 7, 'tref', default=0.0)
        ge = double_or_blank(card, 8, 'ge', default=0.0)
        St = double_or_blank(card, 9, 'St', default=0.0)
        Sc = double_or_blank(card, 10, 'Sc', default=0.0)
        Ss = double_or_blank(card, 11, 'Ss', default=0.0)
        mcsid = integer_or_blank(card, 12, 'mcsid', default=0)
        assert len(card) <= 13, f'len(MAT1 card) = {len(card):d}\ncard={card}'
        self.cards.append((mid, E, G, nu, rho, alpha, tref, ge, St, Sc, Ss,
                           mcsid, comment))
        self.n += 1
        return self.n

    def add_op2_data(self, data, comment: str=''):
        """
        Adds a MAT1 card from the OP2

        Parameters
        ----------
        data : list[varies]
            a list of fields defined in OP2 format
        comment : str; default=''
            a comment for the card

        """
        mid = data[0]
        E = data[1]
        G = data[2]
        nu = data[3]
        rho = data[4]
        alpha = data[5]
        tref = data[6]
        ge = data[7]
        St = data[8]
        Sc = data[9]
        Ss = data[10]
        mcsid = data[11]
        #return MAT1(mid, e, g, nu, rho, a, tref, ge,
                    #St, Sc, Ss, mcsid, comment=comment)
        assert rho is not None, rho
        assert mcsid is not None, mcsid
        self.cards.append((mid, E, G, nu, rho, alpha, tref, ge, St, Sc, Ss,
                           mcsid, comment))
        self.n += 1
        return self.n

    @Material.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)
        material_id = np.zeros(ncards, dtype='int32')
        E = np.zeros(ncards, dtype='float64')
        G = np.zeros(ncards, dtype='float64')
        nu = np.zeros(ncards, dtype='float64')
        rho = np.zeros(ncards, dtype='float64')
        alpha = np.zeros(ncards, dtype='float64')
        tref = np.zeros(ncards, dtype='float64')
        ge = np.zeros(ncards, dtype='float64')
        Ss = np.zeros(ncards, dtype='float64')
        St = np.zeros(ncards, dtype='float64')
        Sc = np.zeros(ncards, dtype='float64')
        mcsid = np.zeros(ncards, dtype='int32')

        for i, card in enumerate(self.cards):
            (mid, Ei, Gi, nui, rhoi, alphai, trefi, gei,
             Sti, Sci, Ssi,
             mcsidi, comment) = card
            material_id[i] = mid
            E[i] = Ei
            G[i] = Gi
            nu[i] = nui
            rho[i] = rhoi
            alpha[i] = alphai
            tref[i] = trefi
            ge[i] = gei
            Ss[i] = Ssi
            St[i] = Sti
            Sc[i] = Sci
            mcsid[i] = mcsidi
        self._save(material_id, E, G, nu, rho, alpha, tref, ge,
                   Ss, St, Sc, mcsid)
        self.sort()
        self.cards = []

    def _save(self, material_id, E, G, nu,
              rho, alpha, tref, ge,
              Ss, St, Sc, mcsid):
        if len(self.material_id):
            material_id = np.hstack([self.material_id, material_id])
            E = np.hstack([self.E, E])
            G = np.hstack([self.G, G])
            nu = np.hstack([self.nu, nu])
            rho = np.hstack([self.rho, rho])
            alpha = np.hstack([self.alpha, alpha])
            tref = np.hstack([self.tref, tref])
            ge = np.hstack([self.ge, ge])
            material_id = np.hstack([self.material_id, material_id])
            Ss = np.hstack([self.Ss, Ss])
            St = np.hstack([self.St, St])
            Sc = np.hstack([self.Sc, Sc])
            mcsid = np.hstack([self.mcsid, mcsid])
        self.material_id = material_id
        self.E = E
        self.G = G
        self.nu = nu
        self.rho = rho
        self.alpha = alpha
        self.tref = tref
        self.ge = ge
        self.Ss = Ss
        self.St = St
        self.Sc = Sc
        self.mcsid = mcsid

    def convert(self, stiffness_scale: float=1.0,
                density_scale: float=1.0,
                alpha_scale: float=1.0,
                temperature_scale: float=1.0,
                stress_scale: float=1.0, **kwargs) -> None:
        self.E *= stiffness_scale
        self.G *= stiffness_scale
        self.rho *= density_scale
        self.alpha *= alpha_scale
        self.Ss *= stress_scale
        self.St *= stress_scale
        self.Sc *= stress_scale

    def __apply_slice__(self, mat: MAT1, i: np.ndarray) -> None:  # ignore[override]
        mat.n = len(i)
        mat.material_id = self.material_id[i]
        mat.E = self.E[i]
        mat.G = self.G[i]
        mat.nu = self.nu[i]
        mat.rho = self.rho[i]
        mat.alpha = self.alpha[i]
        mat.tref = self.tref[i]
        mat.ge = self.ge[i]
        mat.Ss = self.Ss[i]
        mat.St = self.St[i]
        mat.Sc = self.Sc[i]
        mat.mcsid = self.mcsid[i]

    def geom_check(self, missing: dict[str, np.ndarray]):
        pass

    @parse_material_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        max_int = max(self.material_id.max(), self.mcsid.max())
        print_card = get_print_card(size, max_int)
        for mid, e, g, nu, rho, alpha, tref, ge, Ss, St, Sc, \
            mcsid in zip_longest(self.material_id, self.E, self.G, self.nu, self.rho,
                                 self.alpha, self.tref, self.ge,
                                 self.Ss, self.St, self.Sc, self.mcsid):
            g_default = get_G_default(e, g, nu)
            G = set_blank_if_default(g, g_default)

            rho = set_blank_if_default(rho, 0.)
            a = set_blank_if_default(alpha, 0.)
            tref = set_blank_if_default(tref, 0.)
            ge = set_blank_if_default(ge, 0.)

            if [St, Sc, Ss, mcsid] == [0., 0., 0., 0]:
                list_fields = ['MAT1', mid, e, G, nu, rho, a, tref, ge]
            else:
                St = set_blank_if_default(St, 0.)
                Sc = set_blank_if_default(Sc, 0.)
                Ss = set_blank_if_default(Ss, 0.)
                mcsid = set_blank_if_default(mcsid, 0)
                list_fields = ['MAT1', mid, e, G, nu, rho, a, tref, ge,
                               St, Sc, Ss, mcsid]
            bdf_file.write(print_card(list_fields))
        return

    def s33(self):
        """
        ei2 = [
            [  1 / e, -nu / e,    0.],
            [-nu / e,   1 / e,    0.],
            [     0.,      0., 1 / g],
        ]
        """
        nmaterial = len(self.material_id)
        s33 = np.zeros((nmaterial, 3, 3), dtype='float64')
        s33[:, 0, 0] = s33[:, 1, 1] = 1 / self.E
        s33[:, 1, 0] = s33[:, 0, 1] = -self.nu / self.E
        s33[:, 2, 2] = 1 / self.G
        return s33


class MAT2(Material):
    """
    Defines the material properties for linear anisotropic materials for
    two-dimensional elements.

    +------+-------+-----+-----+------+-----+------+-----+-----+
    |   1  |   2   |  3  |  4  |  5   |  6  |  7   | 8   |  9  |
    +======+=======+=====+=====+======+=====+======+=====+=====+
    | MAT2 |  MID  | G11 | G12 | G13  | G22 | G23  | G33 | RHO |
    +------+-------+-----+-----+------+-----+------+-----+-----+
    |      |  A1   | A2  | A3  | TREF | GE  |  ST  | SC  | SS  |
    +------+-------+-----+-----+------+-----+------+-----+-----+
    |      | MCSID |     |     |      |     |      |     |     |
    +------+-------+-----+-----+------+-----+------+-----+-----+

    """
    def add(self, mid: float,
            G11: float, G12: float, G13: float,
            G22: float, G23: float, G33: float, rho: float=0.,
            a1: Optional[float]=None, a2: Optional[float]=None, a3: Optional[float]=None,
            tref: float=0., ge: float=0.,
            St: Optional[float]=None, Sc: Optional[float]=None, Ss: Optional[float]=None,
            mcsid: Optional[int]=None, comment: str='') -> int:
        """Creates an MAT2 card"""
        if a1 is None:
            a1 = np.nan
        if a2 is None:
            a2 = np.nan
        if a3 is None:
            a3 = np.nan

        if St is None:
            St = np.nan
        if Sc is None:
            Sc = np.nan
        if Ss is None:
            Ss = np.nan

        if mcsid is None:
            mcsid = -1
        ge_matrix = [np.nan] * 6
        self.cards.append((mid, G11, G12, G13, G22, G23, G33, rho,
                           [a1, a2, a3], tref, ge, St, Sc, Ss,
                           mcsid, ge_matrix, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        mid = integer(card, 1, 'mid')
        G11 = double_or_blank(card, 2, 'G11', default=0.0)
        G12 = double_or_blank(card, 3, 'G12', default=0.0)
        G13 = double_or_blank(card, 4, 'G13', default=0.0)
        G22 = double_or_blank(card, 5, 'G22', default=0.0)
        G23 = double_or_blank(card, 6, 'G23', default=0.0)
        G33 = double_or_blank(card, 7, 'G33', default=0.0)

        rho = double_or_blank(card, 8, 'rho', default=0.0)
        a1 = double_or_blank(card, 9, 'a1') # blank?
        a2 = double_or_blank(card, 10, 'a2') # blank?
        a3 = double_or_blank(card, 11, 'a3') # blank?
        tref = double_or_blank(card, 12, 'tref', default=0.0)
        ge = double_or_blank(card, 13, 'ge', default=0.0)
        St = double_or_blank(card, 14, 'St') # or blank?
        Sc = double_or_blank(card, 15, 'Sc') # or blank?
        Ss = double_or_blank(card, 16, 'Ss') # or blank?
        mcsid = integer_or_blank(card, 17, 'mcsid', default=-1)

        if len(card) > 18:
            ge_matrix = [
                double_or_blank(card, 18, 'ge11', default=0.0),
                double_or_blank(card, 19, 'ge12', default=0.0),
                double_or_blank(card, 20, 'ge13', default=0.0),
                double_or_blank(card, 21, 'ge22', default=0.0),
                double_or_blank(card, 22, 'ge23', default=0.0),
                double_or_blank(card, 23, 'ge33', default=0.0),
            ]
            assert len(card) <= 24, f'len(MAT2 card) = {len(card):d}\ncard={card}'
            #self.ge_matrix[i, :] = ge_matrix
        else:
            ge_matrix = [np.nan] * 6
            assert len(card) <= 18, f'len(MAT2 card) = {len(card):d}\ncard={card}'
        self.cards.append((mid, G11, G12, G13, G22, G23, G33, rho,
                           [a1, a2, a3], tref, ge, St, Sc, Ss, mcsid, ge_matrix, comment))
        self.n += 1
        return self.n

    @Material.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)
        material_id = np.zeros(ncards, dtype='int32')
        G11 = np.zeros(ncards, dtype='float64')
        G12 = np.zeros(ncards, dtype='float64')
        G13 = np.zeros(ncards, dtype='float64')
        G22 = np.zeros(ncards, dtype='float64')
        G23 = np.zeros(ncards, dtype='float64')
        G33 = np.zeros(ncards, dtype='float64')

        rho = np.zeros(ncards, dtype='float64')
        alpha = np.zeros((ncards, 3), dtype='float64')
        tref = np.zeros(ncards, dtype='float64')
        ge = np.zeros(ncards, dtype='float64')
        Ss = np.zeros(ncards, dtype='float64')
        St = np.zeros(ncards, dtype='float64')
        Sc = np.zeros(ncards, dtype='float64')
        mcsid = np.zeros(ncards, dtype='int32')
        ge_matrix = np.full((ncards, 6), np.nan, dtype='float64')

        for i, card in enumerate(self.cards):
            (mid, G11i, G12i, G13i, G22i, G23i, G33i, rhoi,
             alphas, trefi, gei, Sti, Sci, Ssi, mcsidi, ge_matrixi, comment) = card

            material_id[i] = mid
            G11[i] = G11i
            G12[i] = G12i
            G13[i] = G13i
            G22[i] = G22i
            G23[i] = G23i
            G33[i] = G33i

            rho[i] = rhoi
            alpha[i] = alphas
            tref[i] = trefi
            ge[i] = gei
            Ss[i] = Ssi
            St[i] = Sti
            Sc[i] = Sci
            mcsid[i] = mcsidi
            ge_matrix[i] = ge_matrixi
        self._save(material_id, G11, G12, G13, G22, G23, G33,
                   rho, alpha, tref, ge, Ss, St, Sc,
                   mcsid, ge_matrix)
        self.sort()
        self.cards = []

    def _save(self, material_id, G11, G12, G13, G22, G23, G33,
              rho, alpha, tref, ge, Ss, St, Sc,
              mcsid, ge_matrix):
        if len(self.material_id) != 0:
            raise NotImplementedError()
        #print('calling MAT2 save')
        nmaterial = len(material_id)
        assert nmaterial > 0, nmaterial
        self.material_id = material_id
        self.G11 = G11
        self.G12 = G12
        self.G13 = G13
        self.G22 = G22
        self.G23 = G23
        self.G33 = G33

        self.rho = rho
        self.alpha = alpha
        self.tref = tref
        self.ge = ge
        self.Ss = Ss
        self.St = St
        self.Sc = Sc
        self.mcsid = mcsid
        if ge_matrix is None:
            ge_matrix = np.full((nmaterial, 6), np.nan, dtype='float64')
        self.ge_matrix = ge_matrix
        self.n = len(material_id)

    def convert(self, stiffness_scale: float=1.0,
                density_scale: float=1.0,
                alpha_scale: float=1.0,
                temperature_scale: float=1.0,
                stress_scale: float=1.0, **kwargs) -> None:
        self.G11 *= stiffness_scale
        self.G12 *= stiffness_scale
        self.G13 *= stiffness_scale
        self.G22 *= stiffness_scale
        self.G23 *= stiffness_scale
        self.G33 *= stiffness_scale
        self.rho *= density_scale
        self.alpha *= alpha_scale
        self.Ss *= stress_scale
        self.St *= stress_scale
        self.Sc *= stress_scale

    def validate(self):
        assert isinstance(self.material_id, np.ndarray), self.material_id
        assert isinstance(self.G11, np.ndarray), self.G11
        assert isinstance(self.G12, np.ndarray), self.G12
        assert isinstance(self.G13, np.ndarray), self.G13
        assert isinstance(self.G22, np.ndarray), self.G22
        assert isinstance(self.G23, np.ndarray), self.G23
        assert isinstance(self.G33, np.ndarray), self.G33

        assert isinstance(self.rho, np.ndarray), self.rho
        assert isinstance(self.alpha, np.ndarray), self.alpha
        assert isinstance(self.tref, np.ndarray), self.tref
        assert isinstance(self.ge, np.ndarray), self.ge
        assert isinstance(self.Ss, np.ndarray), self.Ss
        assert isinstance(self.St, np.ndarray), self.St
        assert isinstance(self.Sc, np.ndarray), self.Sc
        assert isinstance(self.mcsid, np.ndarray), self.mcsid
        #if self.ge_matrix is None:
        assert isinstance(self.ge_matrix, np.ndarray), self.ge_matrix

        #print(self.material_id.dtype.name)
        #print(self.G11.dtype.name)
        #print(self.G12.dtype.name)
        #print(self.G13.dtype.name)
        #print(self.G22.dtype.name)
        #print(self.G23.dtype.name)
        #print(self.G33.dtype.name)

        #print(self.rho.dtype.name)
        #print(self.alpha.dtype.name)
        #print(self.tref.dtype.name)
        #print(self.ge.dtype.name)
        #print(self.Ss.dtype.name)
        #print(self.St.dtype.name)
        #print(self.Sc.dtype.name)
        #print(self.mcsid.dtype.name)

    def __apply_slice__(self, mat: MAT2, i: np.ndarray) -> None:  # ignore[override]
        mat.n = len(i)
        mat.material_id = self.material_id[i]
        mat.G11 = self.G11[i]
        mat.G12 = self.G12[i]
        mat.G22 = self.G22[i]
        mat.G33 = self.G33[i]
        mat.G13 = self.G13[i]
        mat.G23 = self.G23[i]
        mat.ge_matrix = self.ge_matrix[i, :]

        mat.rho = self.rho[i]
        mat.alpha = self.alpha[i, :]
        mat.tref = self.tref[i]
        mat.ge = self.ge[i]
        mat.Ss = self.Ss[i]
        mat.St = self.St[i]
        mat.Sc = self.Sc[i]
        mat.mcsid = self.mcsid[i]

    def geom_check(self, missing: dict[str, np.ndarray]):
        pass

    @parse_material_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        max_int = max(self.material_id.max(), self.mcsid.max())
        print_card = get_print_card(size, max_int)
        self.validate()
        #print(self.material_id)
        #print(self.G11)
        #print('G12', self.G12)
        #print(self.G13)
        #print(self.G22)
        #print(self.G23)
        #print(self.G33)
        #print(self.rho)
        #print(self.alpha)
        #print(self.tref)
        #print(self.ge)
        #print(self.Ss)
        #print(self.St)
        #print(self.Sc)
        #print(self.mcsid)
        for mid, G11, G12, G13, G22, G23, G33, \
            rho, (a1, a2, a3), tref, \
            ge, Ss, St, Sc, mcsid in zip_longest(self.material_id,
                                                 self.G11, self.G12, self.G13,
                                                 self.G22, self.G23, self.G33,
                                                 self.rho,
                                                 self.alpha, self.tref, self.ge,
                                                 self.Ss, self.St, self.Sc, self.mcsid):
            G11 = set_blank_if_default(G11, 0.0)
            G12 = set_blank_if_default(G12, 0.0)
            G13 = set_blank_if_default(G13, 0.0)
            G22 = set_blank_if_default(G22, 0.0)
            G23 = set_blank_if_default(G23, 0.0)
            G33 = set_blank_if_default(G33, 0.0)
            rho = set_blank_if_default(rho, 0.0)
            tref = set_blank_if_default(tref, 0.0)
            ge = set_blank_if_default(ge, 0.0)
            list_fields = [
                'MAT2', mid, G11, G12, G13, G22, G23, G33, rho,
                a1, a2, a3, tref, ge,
                St, Sc, Ss, mcsid]
            #if ge_matrix != [0., 0., 0., 0., 0., 0.]:
                #ge11 = set_blank_if_default(ge_matrix[0], 0.0)
                #ge12 = set_blank_if_default(ge_matrix[1], 0.0)
                #ge13 = set_blank_if_default(ge_matrix[2], 0.0)
                #ge22 = set_blank_if_default(ge_matrix[3], 0.0)
                #ge23 = set_blank_if_default(ge_matrix[4], 0.0)
                #ge33 = set_blank_if_default(ge_matrix[5], 0.0)
                #list_fields += [ge11, ge12, ge13, ge22, ge23, ge33]
            bdf_file.write(print_card(list_fields))
        return


class MAT3(Material):
    """
    Defines the material properties for linear orthotropic materials used by
    the CTRIAX6 element entry.

    +------+-----+----+-----+----+-------+-------+------+-----+
    |   1  |  2  |  3 |  4  | 5  |   6   |   7   |  8   |  9  |
    +======+=====+====+=====+====+=======+=======+======+=====+
    | MAT3 | MID | EX | ETH | EZ | NUXTH | NUTHZ | NUZX | RHO |
    +------+-----+----+-----+----+-------+-------+------+-----+
    |      |     |    | GZX | AX |  ATH  |  AZ   | TREF | GE  |
    +------+-----+----+-----+----+-------+-------+------+-----+

    """
    def add(self, mid: int, ex: float, eth: float, ez: float,
            nuxth: float, nuthz: float, nuzx: float,
            rho: float=0.0, gzx: Optional[float]=None,
            ax: float=0., ath: float=0., az: float=0.,
            tref: float=0., ge: float=0.,
            comment: str='') -> int:
        """Creates a MAT3 card"""
        self.cards.append((mid, ex, eth, ez, nuxth, nuthz, nuzx, rho, gzx,
                           ax, ath, az, tref, ge, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        mid = integer(card, 1, 'mid')
        ex = double(card, 2, 'ex')
        eth = double(card, 3, 'eth')
        ez = double(card, 4, 'ez')
        nuxth = double(card, 5, 'nuxth')
        nuthz = double(card, 6, 'nuthz')
        nuzx = double(card, 7, 'nuzx')
        rho = double_or_blank(card, 8, 'rho', default=0.0)

        gzx = double_or_blank(card, 11, 'gzx')
        ax = double_or_blank(card, 12, 'ax', default=0.0)
        ath = double_or_blank(card, 13, 'ath', default=0.0)
        az = double_or_blank(card, 14, 'az', default=0.0)
        tref = double_or_blank(card, 15, 'tref', default=0.0)
        ge = double_or_blank(card, 16, 'ge', default=0.0)
        assert len(card) <= 17, f'len(MAT3 card) = {len(card):d}\ncard={card}'
        self.cards.append((mid, ex, eth, ez, nuxth, nuthz, nuzx, rho, gzx,
                           ax, ath, az, tref, ge, comment))
        self.n += 1
        return self.n

    @Material.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)
        material_id = np.zeros(ncards, dtype='int32')
        ex = np.zeros(ncards, dtype='float64')
        eth = np.zeros(ncards, dtype='float64')
        ez = np.zeros(ncards, dtype='float64')
        nuxth = np.zeros(ncards, dtype='float64')
        nuthz = np.zeros(ncards, dtype='float64')
        nuzx = np.zeros(ncards, dtype='float64')
        gzx = np.zeros(ncards, dtype='float64')

        rho = np.zeros(ncards, dtype='float64')
        ax = np.zeros(ncards, dtype='float64')
        ath = np.zeros(ncards, dtype='float64')
        az = np.zeros(ncards, dtype='float64')
        tref = np.zeros(ncards, dtype='float64')
        ge = np.zeros(ncards, dtype='float64')

        for i, card in enumerate(self.cards):
            (mid, exi, ethi, ezi, nuxthi, nuthzi, nuzxi, rhoi, gzxi,
             axi, athi, azi, trefi, gei, comment) = card
            material_id[i] = mid
            ex[i] = exi
            eth[i] = ethi
            ez[i] = ezi
            nuxth[i] = nuxthi
            nuthz[i] = nuthzi
            nuzx[i] = nuzxi
            gzx[i] = gzxi

            ax[i] = axi
            ath[i] = athi
            az[i] = azi

            rho[i] = rhoi
            tref[i] = trefi
            ge[i] = gei
        self._save(material_id, ex, eth, ez,
                   nuxth, nuthz, nuzx, gzx,
                   ax, ath, az, rho, tref, ge)
        self.sort()
        self.cards = []

    def _save(self, material_id, ex, eth, ez,
              nuxth, nuthz, nuzx, gzx,
              ax, ath, az, rho, tref, ge):
        assert material_id.min() > 0, material_id
        nmaterials = len(material_id)
        self.material_id = material_id
        self.ex = ex
        self.eth = eth
        self.ez = ez
        self.nuxth = nuxth
        self.nuthz = nuthz
        self.nuzx = nuzx
        self.gzx = gzx

        self.ax = ax
        self.ath = ath
        self.az = az

        self.rho = rho
        self.tref = tref
        self.ge = ge
        self.n = nmaterials

    def __apply_slice__(self, mat: MAT3, i: np.ndarray) -> None:
        mat.n = len(i)
        mat.material_id = self.material_id[i]
        mat.ex = self.ex[i]
        mat.eth = self.eth[i]
        mat.ez = self.ez[i]
        mat.nuxth = self.nuxth[i]
        mat.nuthz = self.nuthz[i]
        mat.gzx = self.gzx[i]

        mat.rho = self.rho[i]
        mat.ax = self.ax[i]
        mat.ath = self.ath[i]
        mat.az = self.az[i]
        mat.tref = self.tref[i]
        mat.ge = self.ge[i]

    def geom_check(self, missing: dict[str, np.ndarray]):
        pass

    @parse_material_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        max_int = self.material_id.max()
        print_card = get_print_card(size, max_int)

        material_ids = array_str(self.material_id, size=size)
        for mid, ex, eth, ez, nuxth, nuthz, nuzx, \
            rho, gzx, ax, ath, az, tref, ge in zip_longest(material_ids,
                                                           self.ex, self.eth, self.ez, \
                                                           self.nuxth, self.nuthz, self.nuzx, \
                                                           self.rho, self.gzx, self.ax, self.ath, self.az,
                                                           self.tref, self.ge):
            ax = set_blank_if_default(ax, 0.0)
            ath = set_blank_if_default(ath, 0.0)
            az = set_blank_if_default(az, 0.0)
            rho = set_blank_if_default(rho, 0.0)
            tref = set_blank_if_default(tref, 0.0)
            ge = set_blank_if_default(ge, 0.0)
            list_fields = ['MAT3', mid, ex, eth, ez, nuxth,
                           nuthz, nuzx, rho, None, None, gzx,
                           ax, ath, az, tref, ge]
            bdf_file.write(print_card(list_fields))
        return


class MAT4(Material):
    """
    Defines the constant or temperature-dependent thermal material properties
    for conductivity, heat capacity, density, dynamic viscosity, heat
    generation, reference enthalpy, and latent heat associated with a
    single-phase change.

    +------+-----+--------+------+-----+----+-----+------+---------+
    |   1  |  2  |   3    |   4  |  5  | 6  |  7  |  8   |    9    |
    +======+=====+========+======+=====+====+=====+======+=========+
    | MAT4 | MID |   K    |  CP  | RHO | MU |  H  | HGEN | REFENTH |
    +------+-----+--------+------+-----+----+-----+------+---------+
    |      | TCH | TDELTA | QLAT |     |    |     |      |         |
    +------+-----+--------+------+-----+----+-----+------+---------+

    """
    def add(self, mid: int, k: float, cp: float=0.0, rho: float=1.0,
            H: Optional[float]=None, mu: Optional[float]=None, hgen: float=1.0,
            ref_enthalpy: Optional[float]=None, tch: Optional[float]=None, tdelta: Optional[float]=None,
            qlat: Optional[float]=None, comment: str='') -> int:
        """Creates a MAT4 card"""
        self.cards.append((mid, k, cp, rho, H, mu, hgen, ref_enthalpy, tch, tdelta, qlat, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        mid = integer(card, 1, 'mid')
        k = double_or_blank(card, 2, 'k')
        cp = double_or_blank(card, 3, 'cp', default=0.0)
        rho = double_or_blank(card, 4, 'rho', default=1.0)
        H = double_or_blank(card, 5, 'H')
        mu = double_or_blank(card, 6, 'mu')
        hgen = double_or_blank(card, 7, 'hgen', default=1.0)
        ref_enthalpy = double_or_blank(card, 8, 'refEnthalpy')
        tch = double_or_blank(card, 9, 'tch')
        tdelta = double_or_blank(card, 10, 'tdelta')
        qlat = double_or_blank(card, 11, 'qlat')
        assert len(card) <= 12, f'len(MAT4 card) = {len(card):d}\ncard={card}'
        self.cards.append((mid, k, cp, rho, H, mu, hgen, ref_enthalpy, tch, tdelta, qlat, comment))
        self.n += 1
        return self.n

    @Material.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)
        material_id = np.zeros(ncards, dtype='int32')
        k = np.zeros(ncards, dtype='float64')
        rho = np.zeros(ncards, dtype='float64')

        cp = np.zeros(ncards, dtype='float64')
        H = np.zeros(ncards, dtype='float64')
        mu = np.zeros(ncards, dtype='float64')
        hgen = np.zeros(ncards, dtype='float64')
        ref_enthalpy = np.zeros(ncards, dtype='float64')
        tch = np.zeros(ncards, dtype='float64')
        tdelta = np.zeros(ncards, dtype='float64')
        qlat = np.zeros(ncards, dtype='float64')

        for i, card in enumerate(self.cards):
            (mid, ki, cpi, rhoi, Hi, mui, hgeni, ref_enthalpyi,
             tchi, tdeltai, qlati, comment) = card
            material_id[i] = mid
            k[i] = ki
            cp[i] = cpi
            rho[i] = rhoi
            H[i] = Hi
            mu[i] = mui
            hgen[i] = hgeni
            ref_enthalpy[i] = ref_enthalpyi
            tch[i] = tchi
            tdelta[i] = tdeltai
            qlat[i] = qlati
        self._save(material_id, k, cp, rho, H, mu, hgen, ref_enthalpy,
                   tch, tdelta, qlat)
        self.sort()
        self.cards = []

    def _save(self, material_id, k, cp, rho, H, mu, hgen, ref_enthalpy,
              tch, tdelta, qlat):
        self.material_id = material_id
        self.k = k
        self.rho = rho

        self.cp = cp
        self.H = H
        self.mu = mu
        self.hgen = hgen
        self.ref_enthalpy = ref_enthalpy
        self.tch = tch
        self.tdelta = tdelta
        self.qlat = qlat
        self.n = len(material_id)

    def __apply_slice__(self, mat: MAT4, i: np.ndarray) -> None:
        mat.n = len(i)
        mat.material_id = self.material_id[i]
        mat.k = self.k[i]
        mat.cp = self.cp[i]
        mat.rho = self.rho[i]
        mat.H = self.H[i]
        mat.mu = self.mu[i]
        mat.hgen = self.hgen[i]
        mat.ref_enthalpy = self.ref_enthalpy[i]
        mat.tch = self.tch[i]
        mat.tdelta = self.tdelta[i]
        mat.qlat = self.qlat[i]

    def geom_check(self, missing: dict[str, np.ndarray]):
        pass

    @parse_material_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        max_int = self.material_id.max()
        print_card = get_print_card(size, max_int)
        for mid, k, cp, rho, H, mu, \
            hgen, ref_enthalpy, tch, tdelta, qlat in zip_longest(self.material_id, self.k, self.cp, self.rho, self.H, self.mu,
                                                                 self.hgen, self.ref_enthalpy, self.tch, self.tdelta, self.qlat):
            rhos = set_blank_if_default(rho, 1.0)
            hgens = set_blank_if_default(hgen, 1.0)
            cps = set_blank_if_default(cp, 0.0)
            list_fields = ['MAT4', mid, k, cps, rhos, H, mu, hgens,
                           ref_enthalpy, tch, tdelta, qlat]
            bdf_file.write(print_card(list_fields))
        return


class MAT5(Material):
    """
    Defines the thermal material properties for anisotropic materials.

    +------+-----+-------+-----+-----+-----+-----+-----+----+
    |   1  |  2  |   3   |  4  |  5  |  6  |  7  |  8  | 9  |
    +======+=====+=======+=====+=====+=====+=====+=====+====+
    | MAT5 | MID |  KXX  | KXY | KXZ | KYY | KYZ | KZZ | CP |
    +------+-----+-------+-----+-----+-----+-----+-----+----+
    |      | RHO |  HGEN |     |     |     |     |     |    |
    +------+-----+-------+-----+-----+-----+-----+-----+----+

    """
    def __init__(self, model: BDF):
        super().__init__(model)
        self.kxx = np.zeros(0, dtype='float64')
        self.kxy = np.zeros(0, dtype='float64')
        self.kxz = np.zeros(0, dtype='float64')
        self.kyy = np.zeros(0, dtype='float64')
        self.kyz = np.zeros(0, dtype='float64')
        self.kzz = np.zeros(0, dtype='float64')
        self.cp = np.zeros(0, dtype='float64')
        self.rho = np.zeros(0, dtype='float64')
        self.hgen = np.zeros(0, dtype='float64')

    def add(self, mid: int, kxx: float=0., kxy: float=0., kxz: float=0.,
            kyy: float=0., kyz: float=0., kzz: float=0., cp: float=0.,
            rho: float=1., hgen: float=1., comment: str='') -> int:
        """Creates a MAT5 card"""
        self.cards.append((mid, kxx, kxy, kxz, kyy, kyz, kzz, cp, rho, hgen, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        mid = integer(card, 1, 'mid')
        kxx = double_or_blank(card, 2, 'kxx', default=0.0)
        kxy = double_or_blank(card, 3, 'kxy', default=0.0)
        kxz = double_or_blank(card, 4, 'kxz', default=0.0)
        kyy = double_or_blank(card, 5, 'kyy', default=0.0)
        kyz = double_or_blank(card, 6, 'kyz', default=0.0)
        kzz = double_or_blank(card, 7, 'kzz', default=0.0)

        cp = double_or_blank(card, 8, 'cp', default=0.0)
        rho = double_or_blank(card, 9, 'rho', default=1.0)
        hgen = double_or_blank(card, 10, 'hgen', default=1.0)
        assert len(card) <= 11, f'len(MAT5 card) = {len(card):d}\ncard={card}'
        self.cards.append((mid, kxx, kxy, kxz, kyy, kyz, kzz, cp, rho, hgen, comment))
        self.n += 1
        return self.n

    @Material.parse_cards_check
    def parse_cards(self):
        ncards = len(self.cards)
        material_id = np.zeros(ncards, dtype='int32')
        kxx = np.zeros(ncards, dtype='float64')
        kxy = np.zeros(ncards, dtype='float64')
        kxz = np.zeros(ncards, dtype='float64')
        kyy = np.zeros(ncards, dtype='float64')
        kyz = np.zeros(ncards, dtype='float64')
        kzz = np.zeros(ncards, dtype='float64')
        rho = np.zeros(ncards, dtype='float64')

        cp = np.zeros(ncards, dtype='float64')
        hgen = np.zeros(ncards, dtype='float64')

        for i, card in enumerate(self.cards):
            (mid, kxxi, kxyi, kxzi, kyyi, kyzi, kzzi, cpi, rhoi, hgeni, comment) = card
            material_id[i] = mid
            kxx[i] = kxxi
            kxy[i] = kxyi
            kxz[i] = kxzi
            kyy[i] = kyyi
            kyz[i] = kyzi
            kzz[i] = kzzi
            cp[i] = cpi
            rho[i] = rhoi
            hgen[i] = hgeni
        self._save(material_id, kxx, kxy, kxz, kyy, kyz, kzz, cp, rho, hgen)
        self.sort()
        self.cards = []

    def _save(self, material_id, kxx, kxy, kxz, kyy, kyz, kzz, cp, rho, hgen):
        nmaterials = len(material_id)
        self.material_id = material_id
        self.kxx = kxx
        self.kxy = kxy
        self.kxz = kxz
        self.kyy = kyy
        self.kyz = kyz
        self.kzz = kzz
        self.cp = cp
        self.rho = rho
        self.hgen = hgen
        self.n = nmaterials
        assert material_id.min() >= 1, material_id

    def __apply_slice__(self, mat: MAT5, i: np.ndarray) -> None:
        mat.n = len(i)
        mat.material_id = self.material_id[i]
        mat.kxx = self.kxx[i]
        mat.kxy = self.kxy[i]
        mat.kxz = self.kxz[i]
        mat.kyy = self.kyy[i]
        mat.kyz = self.kyz[i]
        mat.kzz = self.kzz[i]
        mat.cp = self.cp[i]
        mat.rho = self.rho[i]
        mat.hgen = self.hgen[i]

    def geom_check(self, missing: dict[str, np.ndarray]):
        pass

    def k(self):
        """thermal conductivity matrix"""
        k = np.zeros((self.n, 3, 3))
        k[:, 0, 0] = self.kxx
        k[:, 1, 1] = self.kyy
        k[:, 2, 2] = self.kzz
        k[:, 0, 1] = k[:, 1, 0] = self.kxy
        k[:, 0, 2] = k[:, 2, 0] = self.kxz
        k[:, 1, 2] = k[:, 2, 1] = self.kyz
        return k

    @parse_material_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        max_int = self.material_id.max()
        print_card = get_print_card(size, max_int)
        for mid, kxx, kxy, kxz, kyy, kyz, kzz, cp, rho, \
            hgen  in zip_longest(self.material_id,
                                 self.kxx, self.kxy, self.kxz,
                                 self.kyy, self.kyz, self.kzz, self.cp, self.rho,
                                 self.hgen):
            kxx = set_blank_if_default(kxx, 0.0)
            kyy = set_blank_if_default(kyy, 0.0)
            kzz = set_blank_if_default(kzz, 0.0)
            kxy = set_blank_if_default(kxy, 0.0)
            kyz = set_blank_if_default(kyz, 0.0)
            kxz = set_blank_if_default(kxz, 0.0)

            rho = set_blank_if_default(rho, 1.0)
            hgen = set_blank_if_default(hgen, 1.0)
            cp = set_blank_if_default(cp, 0.0)
            list_fields = ['MAT5', mid, kxx, kxy, kxz, kyy, kyz, kzz, cp, rho,
                           hgen]
            bdf_file.write(print_card(list_fields))
        return


class MAT8(Material):
    """
    Defines the material property for an orthotropic material for
    isoparametric shell elements.

    +------+-----+-----+------+------+-----+-----+-----+-----+
    |  1   |  2  |  3  |  4   |  5   |  6  |  7  |  8  |  9  |
    +======+=====+=====+======+======+=====+=====+=====+=====+
    | MAT8 | MID | E1  |  E2  | NU12 | G12 | G1Z | G2Z | RHO |
    +------+-----+-----+------+------+-----+-----+-----+-----+
    |      | A1  |  A2 | TREF |  Xt  |  Xc |  Yt |  Yc |  S  |
    +------+-----+-----+------+------+-----+-----+-----+-----+
    |      | GE1 | F12 | STRN |      |     |     |     |     |
    +------+-----+-----+------+------+-----+-----+-----+-----+

    """
    def __init__(self, model: BDF):
        super().__init__(model)
        self.cards = []
        self.n = 0
        self.material_id = np.array([], dtype='int32')
        self.E11 = np.array([], dtype='float64')
        self.E22 = np.array([], dtype='float64')
        self.G12 = np.array([], dtype='float64')
        self.G13 = np.array([], dtype='float64')
        self.G23 = np.array([], dtype='float64')
        self.nu12 = np.array([], dtype='float64')

        self.rho = np.array([], dtype='float64')
        self.alpha = np.zeros((0, 2), dtype='float64')
        self.tref = np.array([], dtype='float64')
        self.ge = np.array([], dtype='float64')

        self.Xt = np.array([], dtype='float64')
        self.Xc = np.array([], dtype='float64')
        self.Yt = np.array([], dtype='float64')
        self.Yc = np.array([], dtype='float64')
        self.S = np.array([], dtype='float64')
        self.f12 = np.array([], dtype='float64')
        self.strn = np.array([], dtype='float64')

    def add(self, mid: int, e11: float, e22: float, nu12: float,
            g12: float=0.0, g1z: float=1e8, g2z: float=1e8,
            rho: float=0., a1: float=0., a2: float=0., tref: float=0.,
            xt: float=0., xc: Optional[float]=None,
            yt: float=0., yc: Optional[float]=None,
            s: float=0., ge: float=0., f12: float=0., strn: float=0.,
            comment: str='') -> int:
        """Creates a MAT8 card"""
        xc = xc if xc is not None else xt
        yc = yc if yc is not None else yt
        #self.material_id = np.hstack([self.material_id, [mid]])
        #self.E11 = np.hstack([self.E11, [e11]])
        #self.E22 = np.hstack([self.E22, [e22]])
        #self.G12 = np.hstack([self.G12, [g12]])
        #self.G13 = np.hstack([self.G13, [g1z]])
        #self.G23 = np.hstack([self.G23, [g2z]])
        #self.nu12 = np.hstack([self.nu12, [nu12]])
        #self.rho = np.hstack([self.rho, [rho]])
        #self.alpha = np.vstack([self.alpha, [a1, a2]])
        #self.tref = np.hstack([self.tref, [tref]])
        #self.ge = np.hstack([self.ge, [ge]])

        #self.Xt = np.hstack([self.Xt, [Xt]])
        #self.Xc = np.hstack([self.Xc, [Xc]])
        #self.Yt = np.hstack([self.Yt, [Yt]])
        #self.Yc = np.hstack([self.Yc, [Yc]])
        #self.S = np.hstack([self.S, [S]])
        #self.f12 = np.hstack([self.f12, [F12]])
        #self.strn = np.hstack([self.strn, [strn]])
        self.cards.append((mid, e11, e22, nu12, g12, g1z, g2z, rho, [a1, a2], tref,
                           xt, xc, yt, yc, s, ge, f12, strn, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        mid = integer(card, 1, 'mid')
        e11 = double(card, 2, 'E11')    #: .. todo:: is this the correct default
        e22 = double(card, 3, 'E22')    #: .. todo:: is this the correct default

        nu12 = double_or_blank(card, 4, 'nu12', default=0.0)

        g12 = double_or_blank(card, 5, 'g12', default=0.0)
        g1z = double_or_blank(card, 6, 'g1z', default=1e8)
        g2z = double_or_blank(card, 7, 'g2z', default=1e8)
        rho = double_or_blank(card, 8, 'rho', default=0.0)
        a1 = double_or_blank(card, 9, 'a1', default=0.0)
        a2 = double_or_blank(card, 10, 'a2', default=0.0)
        tref = double_or_blank(card, 11, 'tref', default=0.0)
        xt = double_or_blank(card, 12, 'Xt', default=0.0)
        xc = double_or_blank(card, 13, 'Xc', default=xt)
        yt = double_or_blank(card, 14, 'Yt', default=0.0)
        yc = double_or_blank(card, 15, 'Yc', default=yt)
        s = double_or_blank(card, 16, 'S', default=0.0)
        ge = double_or_blank(card, 17, 'ge', default=0.0)
        f12 = double_or_blank(card, 18, 'F12', default=0.0)
        strn = double_or_blank(card, 19, 'strn', default=0.0)
        assert len(card) <= 20, f'len(MAT8 card) = {len(card):d}\ncard={card}'
        self.cards.append((mid, e11, e22, nu12, g12, g1z, g2z, rho, [a1, a2], tref,
                           xt, xc, yt, yc, s, ge, f12, strn, comment))
        self.n += 1
        return self.n

    @Material.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)
        material_id = np.zeros(ncards, dtype='int32')

        E11 = np.zeros(ncards, dtype='float64')
        E22 = np.zeros(ncards, dtype='float64')
        G12 = np.zeros(ncards, dtype='float64')
        G13 = np.zeros(ncards, dtype='float64')
        G23 = np.zeros(ncards, dtype='float64')
        nu12 = np.zeros(ncards, dtype='float64')
        rho = np.zeros(ncards, dtype='float64')
        alpha = np.zeros((ncards, 2), dtype='float64')
        tref = np.zeros(ncards, dtype='float64')
        ge = np.zeros(ncards, dtype='float64')

        Xt = np.zeros(ncards, dtype='float64')
        Xc = np.zeros(ncards, dtype='float64')
        Yt = np.zeros(ncards, dtype='float64')
        Yc = np.zeros(ncards, dtype='float64')
        S = np.zeros(ncards, dtype='float64')
        f12 = np.zeros(ncards, dtype='float64')
        strn = np.zeros(ncards, dtype='float64')

        for icard, card in enumerate(self.cards):
            (mid, e11, e22, nu12i, g12, g1z, g2z, rhoi, alphai, trefi,
             xt, xc, yt, yc, s, gei, f12i, strni, comment) = card
            material_id[icard] = mid
            E11[icard] = e11
            E22[icard] = e22
            G12[icard] = g12
            G13[icard] = g1z
            G23[icard] = g2z
            nu12[icard] = nu12i
            rho[icard] = rhoi
            alpha[icard, :] = alphai  ## thermal expansion in 1 and 2 directions
            tref[icard] = trefi       ## reference temperature
            ge[icard] = gei           ## damping
            Xt[icard] = xt            ## x tension allowable
            Xc[icard] = xc            ## x compression allowable
            Yt[icard] = yt            ## y tension allowable
            Yc[icard] = yc            ## y compression allowable
            S[icard] = s              ## shear allowable
            f12[icard] = f12i
            strn[icard] = strni
        self._save(material_id, E11, E22, G12, G13, G23, nu12,
                   rho, alpha, tref, ge, Xt, Xc, Yt, Yc, S, f12, strn)
        self.sort()
        self.cards = []

    def _save(self, material_id, E11, E22, G12, G13, G23, nu12,
              rho, alpha, tref, ge,
              Xt, Xc, Yt, Yc, S, f12, strn):
        if len(self.material_id) != 0:
            raise NotImplementedError()
        nmaterials = len(material_id)
        self.material_id = material_id
        self.E11 = E11
        self.E22 = E22
        self.G12 = G12
        self.G13 = G13
        self.G23 = G23
        self.nu12 = nu12
        self.rho = rho
        self.alpha = alpha
        self.tref = tref
        self.ge = ge

        self.Xt = Xt
        self.Xc = Xc
        self.Yt = Yt
        self.Yc = Yc
        self.S = S
        self.f12 = f12
        self.strn = strn
        self.n = nmaterials

    def __apply_slice__(self, mat: MAT8, i: np.ndarray) -> None:  # ignore[override]
        mat.n = len(i)
        mat.material_id = self.material_id[i]
        mat.E11 = self.E11[i]
        mat.E22 = self.E22[i]
        mat.G12 = self.G12[i]
        mat.G13 = self.G13[i]
        mat.G23 = self.G23[i]

        mat.nu12 = self.nu12[i]
        mat.rho = self.rho[i]
        mat.alpha = self.alpha[i, :]
        mat.tref = self.tref[i]
        mat.ge = self.ge[i]

        mat.Xt = self.Xt[i]
        mat.Xc = self.Xc[i]
        mat.Yt = self.Yt[i]
        mat.Yc = self.Yc[i]
        mat.S = self.S[i]
        mat.f12 = self.f12[i]
        mat.strn = self.strn[i]

    def convert(self, stiffness_scale: float=1.0,
                density_scale: float=1.0,
                alpha_scale: float=1.0,
                temperature_scale: float=1.0,
                stress_scale: float=1.0, **kwargs) -> None:
        self.E11 *= stiffness_scale
        self.E22 *= stiffness_scale
        self.G12 *= stiffness_scale
        self.G13 *= stiffness_scale
        self.G23 *= stiffness_scale
        self.rho *= density_scale
        self.alpha *= alpha_scale
        self.Xt *= stress_scale
        self.Xc *= stress_scale
        self.Yt *= stress_scale
        self.Yc *= stress_scale
        self.S *= stress_scale

    @property
    def a1(self) -> np.ndarray:
        return self.alpha[:, 0]
    @property
    def a2(self) -> np.ndarray:
        return self.alpha[:, 1]

    @a1.setter
    def a1(self, a1: np.ndarray) -> None:
        self.alpha[:, 0] = a1
    @a2.setter
    def a2(self, a2: np.ndarray) -> None:
        self.alpha[:, 1] = a2

    @property
    def nu21(self):
        """
        ν12*E2 = ν21*E1
        per QRG for MAT8
        """
        nu21 = self.nu12 * self.E22 / self.E11
        return nu21

    def s33(self):
        """
        ei2 = [
            [    1 / e1, -nu21 / e2,      0.],
            [-nu21 / e2,     1 / e2,      0.],
            [        0.,         0., 1 / g12],
        http://web.mit.edu/16.20/homepage/3_Constitutive/Constitutive_files/module_3_with_solutions.pdf
        ]
        """
        nmaterial = len(self.material_id)
        s33 = np.zeros((nmaterial, 3, 3), dtype='float64')
        s33[:, 0, 0] = 1 / self.E11
        s33[:, 1, 1] = 1 / self.E22
        s33[:, 1, 0] = s33[:, 0, 1] = -self.nu21 / self.E22
        s33[:, 2, 2] = 1 / self.G12
        return s33

    def geom_check(self, missing: dict[str, np.ndarray]):
        pass

    @parse_material_check
    def write_file(self, bdf_file: TextIOLike,
              size: int=8, is_double: bool=False,
              write_card_header: bool=False) -> None:
        print_card = get_print_card_8_16(size)
        for mid, e11, e22, g12, g13, g23, nu12, rho, \
            alpha, tref, ge, xt, xc, yt, yc, S, f12, strn, in zip_longest(self.material_id, self.E11, self.E22,
                                                                          self.G12, self.G13, self.G13, self.nu12,
                                                                          self.rho,
                                                                          self.alpha, self.tref, self.ge,
                                                                          self.Xt, self.Xc, self.Yt, self.Yc, self.S,
                                                                          self.f12, self.strn):
            a1, a2 = alpha
            G12 = set_blank_if_default(g12, 0.)
            G1z = set_blank_if_default(g13, 1e8)
            G2z = set_blank_if_default(g23, 1e8)

            rho = set_blank_if_default(rho, 0.0)
            a1 = set_blank_if_default(a1, 0.0)
            a2 = set_blank_if_default(a2, 0.0)
            tref = set_blank_if_default(tref, 0.0)

            xc = set_blank_if_default(xc, xt)
            yc = set_blank_if_default(yc, yt)

            xt = set_blank_if_default(xt, 0.)
            yt = set_blank_if_default(yt, 0.)

            S = set_blank_if_default(S, 0.0)
            ge = set_blank_if_default(ge, 0.0)
            f12 = set_blank_if_default(f12, 0.0)
            strn = set_blank_if_default(strn, 0.0)

            list_fields = ['MAT8', mid, e11, e22, nu12, G12, G1z,
                           G2z, rho, a1, a2, tref, xt, xc, yt, yc, S, ge, f12, strn]
            bdf_file.write(print_card(list_fields))
        return


class MAT9(Material):
    """
    Defines the material properties for linear, temperature-independent,
    anisotropic materials for solid isoparametric elements

    .. seealso::  PSOLID entry description

    +------+-----+-----+-----+-----+-----+------+-----+-----+
    |   1  |  2  | 3   | 4   |  5  |  6  |  7   | 8   |  9  |
    +======+=====+=====+=====+=====+=====+======+=====+=====+
    | MAT9 | MID | G11 | G12 | G13 | G14 | G15  | G16 | G22 |
    +------+-----+-----+-----+-----+-----+------+-----+-----+
    |      | G23 | G24 | G25 | G26 | G33 | G34  | G35 | G36 |
    +------+-----+-----+-----+-----+-----+------+-----+-----+
    |      | G44 | G45 | G46 | G55 | G56 | G66  | RHO | A1  |
    +------+-----+-----+-----+-----+-----+------+-----+-----+
    |      | A2  | A3  | A4  | A5  | A6  | TREF | GE  |     |
    +------+-----+-----+-----+-----+-----+------+-----+-----+

    .. warning:: MSC 2020: gelist is not supported.
    """
    def add(self, mid: int,
            G11=0., G12=0., G13=0., G14=0., G15=0., G16=0.,
            G22=0., G23=0., G24=0., G25=0., G26=0.,
            G33=0., G34=0., G35=0., G36=0.,
            G44=0., G45=0., G46=0.,
            G55=0., G56=0., G66=0.,
            rho=0., A=None, tref=0., ge=0., comment='') -> int:
        if A is None:
            A = [0.] * 6
        self.cards.append((mid, G11, G12, G13, G14, G15, G16,
                           G22, G23, G24, G25, G26,
                           G33, G34, G35, G36,
                           G44, G45, G46,
                           G55, G56, G66, rho, A, tref, ge, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        mid = integer(card, 1, 'mid')
        G11 = double_or_blank(card, 2, 'G11', default=0.0)
        G12 = double_or_blank(card, 3, 'G12', default=0.0)
        G13 = double_or_blank(card, 4, 'G13', default=0.0)
        G14 = double_or_blank(card, 5, 'G14', default=0.0)
        G15 = double_or_blank(card, 6, 'G15', default=0.0)
        G16 = double_or_blank(card, 7, 'G16', default=0.0)
        G22 = double_or_blank(card, 8, 'G22', default=0.0)
        G23 = double_or_blank(card, 9, 'G23', default=0.0)
        G24 = double_or_blank(card, 10, 'G24', default=0.0)
        G25 = double_or_blank(card, 11, 'G25', default=0.0)
        G26 = double_or_blank(card, 12, 'G26', default=0.0)
        G33 = double_or_blank(card, 13, 'G33', default=0.0)
        G34 = double_or_blank(card, 14, 'G34', default=0.0)
        G35 = double_or_blank(card, 15, 'G35', default=0.0)
        G36 = double_or_blank(card, 16, 'G36', default=0.0)
        G44 = double_or_blank(card, 17, 'G44', default=0.0)
        G45 = double_or_blank(card, 18, 'G45', default=0.0)
        G46 = double_or_blank(card, 19, 'G46', default=0.0)
        G55 = double_or_blank(card, 20, 'G55', default=0.0)
        G56 = double_or_blank(card, 21, 'G56', default=0.0)
        G66 = double_or_blank(card, 22, 'G66', default=0.0)
        rho = double_or_blank(card, 23, 'rho', default=0.0)
        alpha = [double_or_blank(card, 24, 'A1', default=0.0),
                 double_or_blank(card, 25, 'A2', default=0.0),
                 double_or_blank(card, 26, 'A3', default=0.0),
                 double_or_blank(card, 27, 'A4', default=0.0),
                 double_or_blank(card, 28, 'A5', default=0.0),
                 double_or_blank(card, 29, 'A6', default=0.0)]
        tref = double_or_blank(card, 30, 'tref', default=0.0)
        ge = double_or_blank(card, 31, 'ge', default=0.0)
        assert len(card) <= 32, f'len(MAT9 card) = {len(card):d}\ncard={card}'
        self.cards.append((mid, G11, G12, G13, G14, G15, G16,
                           G22, G23, G24, G25, G26,
                           G33, G34, G35, G36,
                           G44, G45, G46,
                           G55, G56, G66, rho, alpha, tref, ge, comment))
        self.n += 1
        return self.n

    @Material.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)
        material_id = np.zeros(ncards, dtype='int32')
        G11 = np.zeros(ncards, dtype='float64')
        G12 = np.zeros(ncards, dtype='float64')
        G13 = np.zeros(ncards, dtype='float64')
        G14 = np.zeros(ncards, dtype='float64')
        G15 = np.zeros(ncards, dtype='float64')
        G16 = np.zeros(ncards, dtype='float64')
        G22 = np.zeros(ncards, dtype='float64')
        G23 = np.zeros(ncards, dtype='float64')
        G24 = np.zeros(ncards, dtype='float64')
        G25 = np.zeros(ncards, dtype='float64')
        G26 = np.zeros(ncards, dtype='float64')

        G33 = np.zeros(ncards, dtype='float64')
        G34 = np.zeros(ncards, dtype='float64')
        G35 = np.zeros(ncards, dtype='float64')
        G36 = np.zeros(ncards, dtype='float64')

        G44 = np.zeros(ncards, dtype='float64')
        G45 = np.zeros(ncards, dtype='float64')
        G46 = np.zeros(ncards, dtype='float64')

        G55 = np.zeros(ncards, dtype='float64')
        G56 = np.zeros(ncards, dtype='float64')
        G66 = np.zeros(ncards, dtype='float64')

        rho = np.zeros(ncards, dtype='float64')
        alpha = np.zeros((ncards, 6), dtype='float64')
        tref = np.zeros(ncards, dtype='float64')
        ge = np.zeros(ncards, dtype='float64')

        for icard, card in enumerate(self.cards):
            (mid, G11i, G12i, G13i, G14i, G15i, G16i,
             G22i, G23i, G24i, G25i, G26i,
             G33i, G34i, G35i, G36i,
             G44i, G45i, G46i,
             G55i, G56i, G66i, rhoi, alphai, trefi, gei, comment) = card
            material_id[icard] = mid
            G11[icard] = G11i
            G12[icard] = G12i
            G13[icard] = G13i
            G14[icard] = G14i
            G15[icard] = G15i
            G16[icard] = G16i
            G22[icard] = G22i
            G23[icard] = G23i
            G24[icard] = G24i
            G25[icard] = G25i
            G26[icard] = G26i

            G33[icard] = G33i
            G34[icard] = G34i
            G35[icard] = G35i
            G36[icard] = G36i

            G44[icard] = G44i
            G45[icard] = G45i
            G46[icard] = G46i

            G55[icard] = G55i
            G56[icard] = G56i
            G66[icard] = G66i

            rho[icard] = rhoi
            alpha[icard] = alphai
            tref[icard] = trefi
            ge[icard] = gei
        self._save(material_id, G11, G12, G13, G14, G15, G16,
                   G22, G23, G24, G25, G26,
                   G33, G34, G35, G36,
                   G44, G45, G46,
                   G55, G56,
                   G66, rho, alpha, tref, ge, ge_list=None)
        self.sort()
        self.cards = []

    def _save(self, material_id, G11, G12, G13, G14, G15, G16,
              G22, G23, G24, G25, G26,
              G33, G34, G35, G36,
              G44, G45, G46,
              G55, G56,
              G66, rho, alpha, tref, ge, ge_list):
        if len(self.material_id) != 0:
            raise NotImplementedError()
        nmaterials = len(material_id)
        self.material_id = material_id
        self.G11 = G11
        self.G12 = G12
        self.G13 = G13
        self.G14 = G14
        self.G15 = G15
        self.G16 = G16
        self.G22 = G22
        self.G23 = G23
        self.G24 = G24
        self.G25 = G25
        self.G26 = G26

        self.G33 = G33
        self.G34 = G34
        self.G35 = G35
        self.G36 = G36

        self.G44 = G44
        self.G45 = G45
        self.G46 = G46

        self.G55 = G55
        self.G56 = G56
        self.G66 = G66

        self.rho = rho
        self.alpha = alpha
        self.tref = tref
        self.ge = ge
        if ge_list is None:
            ge_list = np.full((nmaterials, 21), np.nan, dtype=ge.dtype)
        self.ge_list = ge_list
        self.n = nmaterials

    def __apply_slice__(self, mat: MAT9, i: np.ndarray) -> None:  # ignore[override]
        mat.n = len(i)
        mat.material_id = self.material_id[i]
        mat.G11 = self.G11[i]
        mat.G12 = self.G12[i]
        mat.G13 = self.G13[i]
        mat.G14 = self.G14[i]
        mat.G15 = self.G15[i]
        mat.G16 = self.G16[i]
        mat.G22 = self.G22[i]
        mat.G23 = self.G23[i]
        mat.G24 = self.G24[i]
        mat.G25 = self.G25[i]
        mat.G26 = self.G26[i]

        mat.G33 = self.G33[i]
        mat.G34 = self.G34[i]
        mat.G35 = self.G35[i]
        mat.G36 = self.G36[i]
        mat.G44 = self.G44[i]
        mat.G45 = self.G45[i]
        mat.G46 = self.G46[i]
        mat.G55 = self.G55[i]
        mat.G56 = self.G56[i]
        mat.G66 = self.G66[i]

        mat.rho = self.rho[i]
        mat.alpha = self.alpha[i, :]
        mat.tref = self.tref[i]
        mat.ge = self.ge[i]
        mat.ge_list = self.ge_list[i, :]

    def convert(self, stiffness_scale: float=1.0,
                density_scale: float=1.0,
                alpha_scale: float=1.0,
                temperature_scale: float=1.0,
                stress_scale: float=1.0, **kwargs) -> None:
        self.G11 *= stiffness_scale
        self.G12 *= stiffness_scale
        self.G13 *= stiffness_scale
        self.G14 *= stiffness_scale
        self.G15 *= stiffness_scale
        self.G16 *= stiffness_scale
        self.G22 *= stiffness_scale
        self.G23 *= stiffness_scale
        self.G24 *= stiffness_scale
        self.G25 *= stiffness_scale
        self.G26 *= stiffness_scale

        self.G33 *= stiffness_scale
        self.G34 *= stiffness_scale
        self.G35 *= stiffness_scale
        self.G36 *= stiffness_scale
        self.G44 *= stiffness_scale
        self.G45 *= stiffness_scale
        self.G46 *= stiffness_scale
        self.G55 *= stiffness_scale
        self.G56 *= stiffness_scale
        self.G66 *= stiffness_scale

        self.rho *= density_scale
        self.alpha *= alpha_scale
        #self.Xt *= stress_scale
        #self.Xc *= stress_scale
        #self.Yt *= stress_scale
        #self.Yc *= stress_scale
        #self.S *= stress_scale

    def geom_check(self, missing: dict[str, np.ndarray]):
        pass

    @parse_material_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        print_card = get_print_card_8_16(size)
        # TODO: ge_list
        for mid, G11, G12, G13, G14, G15, G16, \
        G22, G23, G24, G25, G26, \
        G33, G34, G35, G36, \
        G44, G45, G46, \
        G55, G56, \
        G66, rho, alpha, tref, \
            ge in zip_longest(self.material_id,
                              self.G11, self.G12, self.G13, self.G14, self.G15, self.G16,
                              self.G22, self.G23, self.G24, self.G25, self.G26,
                              self.G33, self.G34, self.G35, self.G36,
                              self.G44, self.G45, self.G46,
                              self.G55, self.G56,
                              self.G66,
                              self.rho, self.alpha, self.tref, self.ge):
            A = []
            for a in alpha:
                a = set_blank_if_default(a, 0.0)
                A.append(a)

            rho = set_blank_if_default(rho, 0.0)
            tref = set_blank_if_default(tref, 0.0)
            ge = set_blank_if_default(ge, 0.0)
            list_fields = (['MAT9', mid, G11, G12, G13, G14,
                            G15, G16, G22, G23, G24, G25,
                            G26, G33, G34, G35, G36, G44,
                            G45, G46, G55, G56, G66, rho]
                           + A + [tref, ge])
            bdf_file.write(print_card(list_fields))
        return


class MAT10(Material):
    """
    Defines material properties for fluid elements in coupled fluid-structural
    analysis.

    +-------+-----+----------+---------+-----+--------+-----------+-----+-----+
    |   1   |  2  |    3     |    4    |  5  |   6    |     7     |  8  |  9  |
    +=======+=====+==========+=========+=====+========+===========+=====+=====+
    | MAT10 | MID |   BULK   |   RHO   |  C  |   GE   |   ALPHA   |     |     |
    +-------+-----+----------+---------+-----+--------+-----------+-----+-----+

    per MSC 2016

    +-------+-----+----------+---------+-----+--------+-----------+-----+-----+
    |   1   |  2  |    3     |    4    |  5  |   6    |     7     |  8  |  9  |
    +=======+=====+==========+=========+=====+========+===========+=====+=====+
    | MAT10 | MID |   BULK   |   RHO   |  C  |   GE   |   GAMMA   |     |     |
    +-------+-----+----------+---------+-----+--------+-----------+-----+-----+
    |       |     | TID_BULK | TID_RHO |     | TID_GE | TID_GAMMA |     |     |
    +-------+-----+----------+---------+-----+--------+-----------+-----+-----+

    per NX 10

    ..note :: alpha is called gamma

    """
    def __init__(self, model: BDF):
        super().__init__(model)
        self.is_alpha = True

    def add(self, mid: int, bulk: float, rho: float, c: float,
            ge: float=0.0,
            gamma: Optional[float]=None,
            table_bulk: Optional[int]=None,
            table_rho: Optional[int]=None,
            table_ge: Optional[int]=None,
            table_gamma: Optional[int]=None,
            comment: str='') -> int:
        """
        Creates a MAT10 card

        Parameters
        ----------
        mid : int
            material id
        bulk : float; default=None
            Bulk modulus
        rho : float; default=None
            Density
        c : float; default=None
            Speed of sound
        ge : float; default=0.
            Damping
        gamma : float; default=None
            NX : ratio of imaginary bulk modulus to real bulk modulus; default=0.0
            MSC : normalized admittance coefficient for porous material
        table_bulk : int; default=None
            TABLEDx entry defining bulk modulus vs. frequency
            None for MSC Nastran
        table_rho : int; default=None
            TABLEDx entry defining rho vs. frequency
            None for MSC Nastran
        table_ge : int; default=None
            TABLEDx entry defining ge vs. frequency
            None for MSC Nastran
        table_gamma : int; default=None
            TABLEDx entry defining gamma vs. frequency
            None for MSC Nastran
        comment : str; default=''
            a comment for the card

        """
        alpha_gamma = gamma
        self.cards.append((mid, bulk, rho, c, ge, alpha_gamma,
                           table_bulk, table_rho, table_ge, table_gamma, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        mid = integer(card, 1, 'mid')
        bulk = double_or_blank(card, 2, 'bulk')
        rho = double_or_blank(card, 3, 'rho', default=0.0)
        c = double_or_blank(card, 4, 'c', default=np.nan)
        ge = double_or_blank(card, 5, 'ge', default=0.0)

        alpha_gamma = double_or_blank(card, 6, 'gamma', default=np.nan)
        tid_bulk = integer_or_blank(card, 10, 'tid_bulk', default=0)
        tid_rho = integer_or_blank(card, 11, 'tid_rho', default=0)
        tid_ge = integer_or_blank(card, 13, 'tid_ge', default=0)
        tid_gamma = integer_or_blank(card, 14, 'tid_gamma', default=0)
        assert len(card) <= 15, f'len(MAT10 card) = {len(card):d}\ncard={card}'
        self.cards.append((mid, bulk, rho, c, ge, alpha_gamma,
                           tid_bulk, tid_rho, tid_ge, tid_gamma, comment))
        self.n += 1
        return self.n

    @Material.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)
        material_id = np.zeros(ncards, dtype='int32')
        bulk = np.zeros(ncards, dtype='float64')
        c  = np.zeros(ncards, dtype='float64')
        rho = np.zeros(ncards, dtype='float64')
        alpha_gamma = np.zeros(ncards, dtype='float64')
        ge = np.zeros(ncards, dtype='float64')
        table_id_bulk = np.zeros(ncards, dtype='int32')
        table_id_rho = np.zeros(ncards, dtype='int32')
        table_id_ge = np.zeros(ncards, dtype='int32')
        table_id_gamma = np.zeros(ncards, dtype='int32')

        for icard, card in enumerate(self.cards):
            (mid, bulki, rhoi, ci, gei, alpha_gammai,
             tid_bulk, tid_rho, tid_ge, tid_gamma, comment) = card
            if rhoi is None:
                rhoi = 0.0
            if tid_bulk is None:
                tid_bulk = 0
            if tid_rho is None:
                tid_rho = 0
            if tid_ge is None:
                tid_ge = 0
            if tid_gamma is None:
                tid_gamma = 0
            material_id[icard] = mid
            bulk[icard] = bulki
            c[icard] = ci
            rho[icard] = rhoi
            ge[icard] = gei
            alpha_gamma[icard] = alpha_gammai
            table_id_bulk[icard] = tid_bulk
            table_id_rho[icard] = tid_rho
            table_id_ge[icard] = tid_ge
            table_id_gamma[icard] = tid_gamma

        is_alpha = self.model.is_msc
        self._save(material_id, bulk, rho, c, ge, alpha_gamma,
                   table_id_bulk, table_id_rho, table_id_ge, table_id_gamma,
                   is_alpha=is_alpha)
        self.sort()
        self.cards = []

    def _save(self, material_id, bulk, rho, c, ge, alpha_gamma,
              table_id_bulk, table_id_rho, table_id_ge, table_id_gamma,
              is_alpha: bool):
        """is_alpha=True for MSC otherwise False"""
        if len(self.material_id) != 0:
            raise NotImplementedError()
        self.material_id = material_id
        self.bulk = bulk
        self.rho = rho
        self.c = c
        self.ge = ge
        self.alpha_gamma = alpha_gamma
        self.is_alpha = is_alpha

        self.table_id_bulk = table_id_bulk
        self.table_id_rho = table_id_rho
        self.table_id_ge = table_id_ge
        self.table_id_gamma = table_id_gamma
        self.n = len(material_id)

    def convert(self, pressure_scale: float=1.0,
                velocity_scale: float=1.0,
                temperature_scale: float=1.0,
                alpha_scale: float=1.0, **kwargs) -> None:
        self.bulk *= pressure_scale
        self.c *= velocity_scale
        ialpha = (self.is_alpha == 1)
        self.alpha_gamma[ialpha] *= alpha_scale

    #def _save_msc(self, material_id, bulk, rho, c, ge, alpha):
        #nmaterial = len(material_id)
        #self.material_id = material_id
        #self.bulk = bulk
        #self.rho = rho
        #self.c = c
        #self.ge = ge
        #if alpha is None:
            #alpha = np.zeros(nmaterial, dtype=bulk.dtype)
        #self.alpha_gamma = alpha
        #self.is_alpha = True
        #self.n = nmaterial
        #assert material_id.min() >= 1, material_id

    def _save_msc(self, material_id, bulk, rho, c, ge, alpha):
        nmaterials = len(material_id)
        self.material_id = material_id
        self.bulk = bulk
        self.rho = rho
        self.c = c
        self.ge = ge
        if alpha is None:
            alpha = np.zeros(nmaterials, dtype=bulk.dtype)
        self.alpha_gamma = alpha
        self.is_alpha = True
        self.n = nmaterials
        assert alpha is not None

        self.table_id_bulk = np.zeros(nmaterials, dtype=material_id.dtype)
        self.table_id_rho = np.zeros(nmaterials, dtype=material_id.dtype)
        self.table_id_ge = np.zeros(nmaterials, dtype=material_id.dtype)
        self.table_id_gamma = np.zeros(nmaterials, dtype=material_id.dtype)

    def __apply_slice__(self, mat: MAT10, i: np.ndarray) -> None:  # ignore[override]
        mat.n = len(i)
        mat.material_id = self.material_id[i]
        mat.bulk = self.bulk[i]
        mat.c = self.c[i]
        mat.rho = self.rho[i]
        mat.ge = self.ge[i]
        mat.alpha_gamma = self.alpha_gamma[i]
        mat.table_id_bulk = self.table_id_bulk[i]
        mat.table_id_rho = self.table_id_rho[i]
        mat.table_id_ge = self.table_id_ge[i]
        mat.table_id_gamma = self.table_id_gamma[i]

    def geom_check(self, missing: dict[str, np.ndarray]):
        pass

    @parse_material_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        print_card = get_print_card_8_16(size)
        material_ids = array_str(self.material_id)
        for mid, bulk, rho, c, ge, gamma, \
            table_bulk, table_rho, table_ge, table_gamma in zip_longest(
                material_ids, self.bulk, self.rho, self.c, self.ge, self.alpha_gamma,
                self.table_id_bulk, self.table_id_rho, self.table_id_ge, self.table_id_gamma):

            rho = set_blank_if_default(rho, 0.)
            list_fields = [
                'MAT10', mid, bulk, rho, c, ge, gamma,
                None, None, None,
                table_bulk, table_rho, None, table_ge, table_gamma
            ]
            list_fields = ['' if isinstance(value, float) and np.isnan(value) else value
                           for value in list_fields]
            bdf_file.write(print_card(list_fields))
        return


class MAT11(Material):
    """
    Defines the material properties for a 3D orthotropic material for
    isoparametric solid elements.

    +-------+-----+-----+-----+----+------+------+------+-----+
    |   1   |  2  |  3  |  4  |  5 |   6  |  7   |  8   |  9  |
    +=======+=====+=====+=====+====+======+======+======+=====+
    | MAT11 | MID |  E1 | E2  | E3 | NU12 | NU13 | NU23 | G12 |
    +-------+-----+-----+-----+----+------+------+------+-----+
    |       | G13 | G23 | RHO | A1 |  A2  |  A3  | TREF | GE  |
    +-------+-----+-----+-----+----+------+------+------+-----+

    """
    def add(self, mid: int, e1: float, e2: float, e3: float,
            nu12: float, nu13: float, nu23: float,
            g12: float, g13: float, g23: float,
            rho: float=0.0,
            a1: float=0.0, a2: float=0.0, a3: float=0.0,
            tref: float=0.0, ge: float=0.0, comment: str='') -> int:
        """Creates a MAT11 card"""
        self.cards.append((mid, e1, e2, e3, nu12, nu13, nu23, g12, g13, g23,
                           rho, a1, a2, a3, tref, ge, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        mid = integer(card, 1, 'mid')
        e1 = double(card, 2, 'E1')
        e2 = double(card, 3, 'E2')
        e3 = double(card, 4, 'E3')

        nu12 = double(card, 5, 'nu12')
        nu13 = double(card, 6, 'nu13')
        nu23 = double(card, 7, 'nu23')

        g12 = double(card, 8, 'g12')
        g13 = double(card, 9, 'g13')
        g23 = double(card, 10, 'g23')

        rho = double_or_blank(card, 11, 'rho', default=0.0)
        a1 = double_or_blank(card, 12, 'a1', default=0.0)
        a2 = double_or_blank(card, 13, 'a2', default=0.0)
        a3 = double_or_blank(card, 14, 'a3', default=0.0)

        tref = double_or_blank(card, 15, 'tref', default=0.0)
        ge = double_or_blank(card, 16, 'ge', default=0.0)
        assert len(card) <= 17, f'len(MAT11 card) = {len(card):d}\ncard={card}'
        self.cards.append((mid, e1, e2, e3, nu12, nu13, nu23, g12, g13, g23,
                           rho, a1, a2, a3, tref, ge, comment))
        self.n += 1

    @Material.parse_cards_check
    def parse_cards(self) -> None:
        ncards = len(self.cards)
        self.material_id = np.zeros(ncards, dtype='int32')
        self.bulk = np.zeros(ncards, dtype='float64')

        self.e1 = np.zeros(ncards, dtype='float64')
        self.e2 = np.zeros(ncards, dtype='float64')
        self.e3 = np.zeros(ncards, dtype='float64')

        self.nu12 = np.zeros(ncards, dtype='float64')
        self.nu13 = np.zeros(ncards, dtype='float64')
        self.nu23 = np.zeros(ncards, dtype='float64')

        self.g12 = np.zeros(ncards, dtype='float64')
        self.g13 = np.zeros(ncards, dtype='float64')
        self.g23 = np.zeros(ncards, dtype='float64')

        self.alpha1 = np.zeros(ncards, dtype='float64')
        self.alpha2 = np.zeros(ncards, dtype='float64')
        self.alpha3 = np.zeros(ncards, dtype='float64')

        self.tref = np.zeros(ncards, dtype='float64')
        self.ge = np.zeros(ncards, dtype='float64')
        self.rho = np.zeros(ncards, dtype='float64')

        self.ge = np.zeros(ncards, dtype='float64')

        for i, card in enumerate(self.cards):
            (mid, e1, e2, e3, nu12, nu13, nu23, g12, g13, g23, rhoi, a1, a2, a3, tref, ge, comment) = card
            self.material_id[i] = mid
            self.e1[i] = e1
            self.e2[i] = e2
            self.e3[i] = e3

            self.nu12[i] = nu12
            self.nu13[i] = nu13
            self.nu23[i] = nu23

            self.g12[i] = g12
            self.g13[i] = g13
            self.g23[i] = g23

            self.alpha1[i] = a1
            self.alpha2[i] = a2
            self.alpha3[i] = a3
            self.rho[i] = rhoi
            self.tref[i] = tref
            self.ge[i] = ge
        self.sort()
        self.cards = []

    def __apply_slice__(self, mat: MAT11, i: np.ndarray) -> None:
        mat.n = len(i)
        mat.material_id = self.material_id[i]

        mat.e1 = self.e1[i]
        mat.e2 = self.e2[i]
        mat.e3 = self.e3[i]

        mat.nu12 = self.nu12[i]
        mat.nu13 = self.nu13[i]
        mat.nu23 = self.nu23[i]

        mat.g12 = self.g12[i]
        mat.g13 = self.g13[i]
        mat.g23 = self.g23[i]

        mat.alpha1 = self.alpha1[i]
        mat.alpha2 = self.alpha2[i]
        mat.alpha3 = self.alpha3[i]
        mat.tref = self.tref[i]
        mat.ge = self.ge[i]
        mat.rho = self.rho[i]

        #mat.bulk = self.bulk[i]
        #mat.c = self.c[i]
        #mat.rho = self.rho[i]
        #mat.ge = self.ge[i]
        #mat.gamma = self.gamma[i]
        #mat.table_id_bulk = self.table_id_bulk[i]
        #mat.table_id_rho = self.table_id_rho[i]
        #mat.table_id_ge = self.table_id_ge[i]
        #mat.table_id_gamma = self.table_id_gamma[i]

    def geom_check(self, missing: dict[str, np.ndarray]):
        pass

    @parse_material_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        print_card = get_print_card_8_16(size)
        material_ids = array_str(self.material_id)
        for mid, e1, e2, e3, nu12, nu13, nu23, \
            g12, g13, g23, rho, a1, a2, a3, tref, ge in zip_longest(material_ids, self.e1, self.e2, self.e3,
                                                                    self.nu12, self.nu13, self.nu23,
                                                                    self.g12, self.g13, self.g23, self.rho,
                                                                    self.alpha1, self.alpha2, self.alpha3, self.tref, self.ge):

            a1 = set_blank_if_default(a1, 0.0)
            a2 = set_blank_if_default(a2, 0.0)
            a3 = set_blank_if_default(a3, 0.0)

            tref = set_blank_if_default(tref, 0.0)
            rho = set_blank_if_default(rho, 0.0)
            ge = set_blank_if_default(ge, 0.0)

            list_fields = ['MAT11', mid, e1, e2, e3, nu12,
                           nu13, nu23, g12, g13, g23, rho, a1,
                           a2, a3, tref, ge]
            bdf_file.write(print_card(list_fields))


class MAT10C(Material):
    """
    Fluid or Absorber Material Property Definition in Complex Format

    Defines constant or nominal material properties for fluid or absorber elements in
    coupled fluid-structural analysis.

    +--------+-----+----------+---------+------+--------+--------+-----+-----+
    |    1   |  2  |    3     |    4    |  5   |   6    |    7   |  8  |  9  |
    +========+=====+==========+=========+======+========+========+=====+=====+
    | MAT10C | MID |   FORM   |   RHOR  | RHOI |   CR   |   CI   |     |     |
    +--------+-----+----------+---------+------+--------+--------+-----+-----+

    per NX 2019.2

    """
    def __init__(self, model: BDF):
        super().__init__(model)

    def add(self, mid: int, form: str='REAL',
            rho_real: float=0.0, rho_imag: float=0.0,
            c_real: float=0.0, c_imag: float=0.0,
            comment: str=''):
        assert form in {'REAL', 'IMAG'}, f'form={form!r}'
        self.cards.append((mid, form, rho_real, rho_imag, c_real, c_imag, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        #ID Material identification number. (Integer > 0)
        #FORM Format to define the fluid density and speed of sound. (Character; REAL or PHASE; Default=REAL)
        # - REAL, define the fluid density and speed of sound in rectangular format (real and imaginary).
        # - PHASE, define the fluid density and speed of sound in polar format (magnitude and phase).
        #RHOR Real part of density. (Real; Default=0.0)
        #RHOI Imaginary part of density. (Real; Default=0.0)
        #CR Real part of speed of sound. (Real; Default=0.0)
        #CI Imaginary part of speed of sound. (Real; Default=0.0)
        mid = integer(card, 1, 'mid')
        form = string_or_blank(card, 2, 'form', default='REAL')
        assert form in {'REAL', 'IMAG'}, f'form={form!r}'
        rho_real = double_or_blank(card, 3, 'rho_real', default=0.0)
        rho_imag = double_or_blank(card, 4, 'rho_imag', default=0.0)
        c_real = double_or_blank(card, 5, 'sos_real', default=0.0)
        c_imag = double_or_blank(card, 6, 'sos_imag', default=0.0)

        assert len(card) <= 7, f'len(MAT10C card) = {len(card):d}\ncard={card}'
        self.cards.append((mid, form, rho_real, rho_imag, c_real, c_imag, comment))
        self.n += 1
        return self.n

    @Material.parse_cards_check
    def parse_cards(self):
        ncards = len(self.cards)
        material_id = np.zeros(ncards, dtype='int32')
        form = np.zeros(ncards, dtype='|U4')
        c  = np.zeros(ncards, dtype='complex128')
        rho = np.zeros(ncards, dtype='complex128')

        for icard, card in enumerate(self.cards):
            (mid, formi, rho_real, rho_imag, c_real, c_imag, comment) = card
            material_id[icard] = mid
            form[icard] = formi
            c[icard] = c_real + 1j * c_imag
            rho[icard] = rho_real + 1j * rho_imag

        self._save(material_id, form, rho, c)
        self.sort()
        self.cards = []

    def _save(self, material_id, form, rho, c):
        self.material_id = material_id
        self.form = form
        self.rho = rho
        self.c = c
        self.n = len(material_id)

    def convert(self,
                velocity_scale: float=1.0,
                density_scale: float=1.0, **kwargs) -> None:
        self.c *= velocity_scale
        self.rho *= density_scale

    def __apply_slice__(self, mat: MAT10C, i: np.ndarray) -> None:
        mat.n = len(i)
        mat.material_id = self.material_id[i]
        mat.form = self.form[i]
        mat.c = self.c[i]
        mat.rho = self.rho[i]

    def geom_check(self, missing: dict[str, np.ndarray]):
        pass

    @parse_material_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        max_int = self.material_id.max()
        print_card = get_print_card(size, max_int)

        material_ids = array_str(self.material_id)
        for mid, form, rhor, rhoi, cr, ci in zip_longest(
                material_ids, self.form, self.rho.real, self.rho.imag, self.c.real, self.c.imag):

            list_fields = [
                'MAT10C', mid, form, rhor, rhoi, cr, ci]
            bdf_file.write(print_card(list_fields))
        return


class MATORT(Material):
    """
    Defines the material properties for linear isotropic materials.

    +--------+--------+-------+-------+-----+------+------+------+-----+
    |    1   |    2   |   3   |   4   |  5  |   6  |  7   |  8   |  9  |
    +========+========+=======+=======+=====+======+======+======+=====+
    | MATORT |   MID  |   E1  |   E2  |  E3 | NU12 | NU23 | NU31 | RHO |
    +--------+--------+-------+-------+-----+------+------+------+-----+
    |        |   G12  |  G23  |  G31  |  A1 |  A2  |  A3  | TREF |  GE |
    +--------+--------+-------+-------+-----+------+------+------+-----+
    |        |  IYLD  | IHARD |   SY  |     |  Y1  |  Y2  |  Y3  | N/A |
    +--------+--------+-------+-------+-----+------+------+------+-----+
    |        |  Yshr1 | Yshr2 | Yshr3 | N/A | N/A  |  N/A |  N/A | N/A |
    +--------+--------+-------+-------+-----+------+------+------+-----+
    |        | OPTION |  FILE |   X1  |  Y1 |  Z1  |  X2  |  Y2  |  Z2 |
    +--------+--------+-------+-------+-----+------+------+------+-----+
    """
    def __init__(self, model: BDF):
        super().__init__(model)
        self.cards = []
        self.n = 0
        self.material_id = np.array([], dtype='int32')
        self.E1 = np.zeros([], dtype='float64')
        self.E2 = np.zeros([], dtype='float64')
        self.E3 = np.zeros([], dtype='float64')

        self.G12 = np.array([], dtype='float64')
        self.G23 = np.array([], dtype='float64')
        self.G31 = np.array([], dtype='float64')

        self.nu = np.array([], dtype='float64')
        self.rho = np.array([], dtype='float64')

        self.alpha1 = np.array([], dtype='float64')
        self.alpha2 = np.array([], dtype='float64')
        self.alpha3 = np.array([], dtype='float64')

        self.tref = np.array([], dtype='float64')
        self.ge = np.array([], dtype='float64')

    def add(self, mid: int, E1: float, E2: float, E3: float,
            nu12: float, nu23: float, nu31: float,
            G12: float, G23: float, G31: float,
            rho: float=0.0,
            alpha1: float=0.0, alpha2: float=0.0, alpha3: float=0.0,
            tref: float=0.0, ge: float=0.0,
            comment: str=''):
        self.cards.append((mid, E1, E2, E3, nu12, nu23, nu31, rho, G12, G23, G31,
                           alpha1, alpha2, alpha3, tref, ge, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        #| MATORT |   MID  |   E1  |   E2  |  E3 | NU12 | NU23 | NU31 | RHO |
        #|        |   G12  |  G23  |  G31  |  A1 |  A2  |  A3  | TREF |  GE |
        #|        |  IYLD  | IHARD |   SY  |     |  Y1  |  Y2  |  Y3  | N/A |
        #|        |  Yshr1 | Yshr2 | Yshr3 | N/A | N/A  |  N/A |  N/A | N/A |
        #|        | OPTION |  FILE |   X1  |  Y1 |  Z1  |  X2  |  Y2  |  Z2 |
        mid = integer(card, 1, 'mid')
        E1 = double_or_blank(card, 2, 'E1')
        E2 = double_or_blank(card, 3, 'E2')
        E3 = double_or_blank(card, 4, 'E3')

        nu12 = double_or_blank(card, 5, 'nu12')
        nu23 = double_or_blank(card, 6, 'nu23')
        nu31 = double_or_blank(card, 7, 'nu31')
        rho = double_or_blank(card, 8, 'rho', default=0.)

        G12 = double_or_blank(card, 9, 'G12')
        G23 = double_or_blank(card, 10, 'G23')
        G31 = double_or_blank(card, 11, 'G31')

        alpha1 = double_or_blank(card, 12, 'a1', default=0.0)
        alpha2 = double_or_blank(card, 13, 'a2', default=0.0)
        alpha3 = double_or_blank(card, 14, 'a3', default=0.0)

        tref = double_or_blank(card, 15, 'tref', default=0.0)
        ge = double_or_blank(card, 16, 'ge', default=0.0)
        assert len(card) <= 18, f'len(MATORT card) = {len(card):d}\ncard={card}'
        self.cards.append((mid, E1, E2, E3, nu12, nu23, nu31, rho, G12, G23, G31,
                           alpha1, alpha2, alpha3, tref, ge, comment))
        self.n += 1
        return self.n

    @Material.parse_cards_check
    def parse_cards(self):
        ncards = len(self.cards)
        material_id = np.zeros(ncards, dtype='int32')
        E1 = np.zeros(ncards, dtype='float64')
        E2 = np.zeros(ncards, dtype='float64')
        E3 = np.zeros(ncards, dtype='float64')
        G12 = np.zeros(ncards, dtype='float64')
        G23 = np.zeros(ncards, dtype='float64')
        G31 = np.zeros(ncards, dtype='float64')

        nu12 = np.zeros(ncards, dtype='float64')
        nu23 = np.zeros(ncards, dtype='float64')
        nu31 = np.zeros(ncards, dtype='float64')
        rho = np.zeros(ncards, dtype='float64')
        alpha1 = np.zeros(ncards, dtype='float64')
        alpha2 = np.zeros(ncards, dtype='float64')
        alpha3 = np.zeros(ncards, dtype='float64')
        tref = np.zeros(ncards, dtype='float64')
        ge = np.zeros(ncards, dtype='float64')

        for i, card in enumerate(self.cards):
            (mid, E1i, E2i, E3i, nu12i, nu23i, nu31i, rhoi, G12i, G23i, G31i,
             alpha1i, alpha2i, alpha3i, trefi, gei, comment) = card
            material_id[i] = mid
            E1[i] = E1i
            E2[i] = E2i
            E3[i] = E3i
            G12[i] = G12i
            G23[i] = G23i
            G31[i] = G31i

            nu12[i] = nu12i
            nu23[i] = nu23i
            nu31[i] = nu31i

            rho[i] = rhoi
            alpha1[i] = alpha1i
            alpha2[i] = alpha2i
            alpha3[i] = alpha3i
            tref[i] = trefi
            ge[i] = gei
        self._save(material_id, E1, E2, E3, nu12, nu23, nu31, G12, G23, G31,
                   rho, alpha1, alpha2, alpha3, tref, ge)
        self.sort()
        self.cards = []

    def _save(self, material_id, E1, E2, E3, nu12, nu23, nu31, G12, G23, G31,
                   rho, alpha1, alpha2, alpha3, tref, ge):
        assert len(self.material_id) == 0, self.material_id
        self.material_id = material_id
        self.E1 = E1
        self.E2 = E2
        self.E3 = E3
        self.G12 = G12
        self.G23 = G23
        self.G31 = G31
        self.nu12 = nu12
        self.nu23 = nu23
        self.nu31 = nu31
        self.rho = rho
        self.alpha1 = alpha1
        self.alpha2 = alpha2
        self.alpha3 = alpha3
        self.tref = tref
        self.ge = ge
        assert len(self.material_id) > 0, self.material_id
        #self.model.log.warning('saved MATORT')

    def __apply_slice__(self, mat: MATORT, i: np.ndarray) -> None:
        mat.n = len(i)
        mat.material_id = self.material_id[i]
        mat.E1 = self.E1[i]
        mat.E2 = self.E2[i]
        mat.E3 = self.E3[i]
        mat.G12 = self.G12[i]
        mat.G23 = self.G23[i]
        mat.G31 = self.G31[i]
        mat.nu12 = self.nu12[i]
        mat.nu23 = self.nu23[i]
        mat.nu31 = self.nu31[i]
        mat.rho = self.rho[i]
        mat.alpha1 = self.alpha1[i]
        mat.alpha2 = self.alpha2[i]
        mat.alpha3 = self.alpha3[i]
        mat.tref = self.tref[i]
        mat.ge = self.ge[i]

    def geom_check(self, missing: dict[str, np.ndarray]):
        pass

    @parse_material_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        max_int = self.material_id.max()
        print_card = get_print_card(size, max_int)

        for mid, e1, e2, e3, g12, g23, g31, nu12, nu23, nu31, \
            rho, alpha1, alpha2, alpha3, tref, ge, \
            in zip_longest(self.material_id, self.E1, self.E2, self.E3,
                           self.G12, self.G23, self.G31,
                           self.nu12, self.nu23, self.nu31, self.rho,
                           self.alpha1, self.alpha2, self.alpha3, self.tref, self.ge):

            rho = set_blank_if_default(rho, 0.)
            a1 = set_blank_if_default(alpha1, 0.)
            a2 = set_blank_if_default(alpha2, 0.)
            a3 = set_blank_if_default(alpha3, 0.)
            tref = set_blank_if_default(tref, 0.)
            ge = set_blank_if_default(ge, 0.)

            list_fields = ['MATORT', mid, e1, e2, e3, nu12, nu23, nu31, rho,
                           g12, g23, g31, a1, a2, a3, tref, ge]
            bdf_file.write(print_card(list_fields))
        return

    #def s33(self):
        #"""
        #ei2 = [
            #[  1 / e, -nu / e,    0.],
            #[-nu / e,   1 / e,    0.],
            #[     0.,      0., 1 / g],
        #]
        #"""
        #nmaterial = len(self.material_id)
        #s33 = np.zeros((nmaterial, 3, 3), dtype='float64')
        #s33[:, 0, 0] = s33[:, 1, 1] = 1 / self.E
        #s33[:, 1, 0] = s33[:, 0, 1] = -self.nu / self.E
        #s33[:, 2, 2] = 1 / self.G
        #return s33


class MATHP(Material):
    def add(self, mid: int, a10=0., a01=0., d1=None, rho=0., av=0., tref=0., ge=0., na=1, nd=1,
            a20=0., a11=0., a02=0., d2=0.,
            a30=0., a21=0., a12=0., a03=0., d3=0.,
            a40=0., a31=0., a22=0., a13=0., a04=0., d4=0.,
            a50=0., a41=0., a32=0., a23=0., a14=0., a05=0., d5=0.,
            tab1=None, tab2=None, tab3=None, tab4=None, tabd=None, comment=''):
        #HyperelasticMaterial.__init__(self)
        if comment:
            self.comment = comment
        if d1 is None:
            d1 = (a10 + a01) * 1000.

        self.cards.append((mid, a10, a01, d1, rho, av, tref, ge, na, nd, a20, a11,
                           a02, d2, a30, a21, a12, a03, d3, a40,
                           a31, a22, a13, a04, d4, a50, a41,
                           a32, a23, a14, a05, d5, tab1, tab2,
                           tab3, tab4, tabd, comment))
        self.n += 1
        return self.n

    def add_card(self, card: BDFCard, comment: str='') -> int:
        """
        Adds a MATHP card from ``BDF.add_card(...)``

        Parameters
        ----------
        card : BDFCard()
            a BDFCard object
        comment : str; default=''
            a comment for the card

        """
        mid = integer(card, 1, 'mid')
        a10 = double_or_blank(card, 2, 'a10', default=0.)
        a01 = double_or_blank(card, 3, 'a01', default=0.)
        d1 = double_or_blank(card, 4, 'd1', default=(a10 + a01) * 1000)
        rho = double_or_blank(card, 5, 'rho', default=0.)
        av = double_or_blank(card, 6, 'av', default=0.)
        tref = double_or_blank(card, 7, 'tref', default=0.)
        ge = double_or_blank(card, 8, 'ge', default=0.)

        na = integer_or_blank(card, 10, 'na', default=1)
        nd = integer_or_blank(card, 11, 'nd', default=1)

        a20 = double_or_blank(card, 17, 'a20', default=0.)
        a11 = double_or_blank(card, 18, 'a11', default=0.)
        a02 = double_or_blank(card, 19, 'a02', default=0.)
        d2 = double_or_blank(card, 20, 'd2', default=0.)

        a30 = double_or_blank(card, 25, 'a30', default=0.)
        a21 = double_or_blank(card, 26, 'a21', default=0.)
        a12 = double_or_blank(card, 27, 'a12', default=0.)
        a03 = double_or_blank(card, 28, 'a03', default=0.)
        d3 = double_or_blank(card, 29, 'd3', default=0.)

        a40 = double_or_blank(card, 33, 'a40', default=0.)
        a31 = double_or_blank(card, 34, 'a31', default=0.)
        a22 = double_or_blank(card, 35, 'a22', default=0.)
        a13 = double_or_blank(card, 36, 'a13', default=0.)
        a04 = double_or_blank(card, 37, 'a04', default=0.)
        d4 = double_or_blank(card, 38, 'd4', default=0.)

        a50 = double_or_blank(card, 41, 'a50', default=0.)
        a41 = double_or_blank(card, 42, 'a41', default=0.)
        a32 = double_or_blank(card, 43, 'a32', default=0.)
        a23 = double_or_blank(card, 44, 'a23', default=0.)
        a14 = double_or_blank(card, 45, 'a14', default=0.)
        a05 = double_or_blank(card, 46, 'a05', default=0.)
        d5 = double_or_blank(card, 47, 'd5', default=0.)

        tab1 = integer_or_blank(card, 49, 'tab1', default=0)
        tab2 = integer_or_blank(card, 50, 'tab2', default=0)
        tab3 = integer_or_blank(card, 51, 'tab3', default=0)
        tab4 = integer_or_blank(card, 52, 'tab4', default=0)
        tabd = integer_or_blank(card, 56, 'tabd', default=0)
        assert len(card) <= 57, f'len(MATHP card) = {len(card):d}\ncard={card}'
        #return MATHP(mid, a10, a01, d1, rho, av, tref, ge, na, nd, a20, a11,
                     #a02, d2, a30, a21, a12, a03, d3, a40,
                     #a31, a22, a13, a04, d4, a50, a41,
                     #a32, a23, a14, a05, d5, tab1, tab2,
                     #tab3, tab4, tabd, comment=comment)
        self.cards.append((mid, a10, a01, d1, rho, av, tref, ge, na, nd, a20, a11,
                           a02, d2, a30, a21, a12, a03, d3, a40,
                           a31, a22, a13, a04, d4, a50, a41,
                           a32, a23, a14, a05, d5, tab1, tab2,
                           tab3, tab4, tabd, comment))
        self.n += 1
        return self.n

    @Material.parse_cards_check
    def parse_cards(self):
        ncards = len(self.cards)
        material_id = np.zeros(ncards, dtype='int32')
        a10 = np.zeros(ncards, dtype='float64')
        a01 = np.zeros(ncards, dtype='float64')
        d1 = np.zeros(ncards, dtype='float64')
        rho = np.zeros(ncards, dtype='float64')
        av = np.zeros(ncards, dtype='float64')
        tref = np.zeros(ncards, dtype='float64')
        ge = np.zeros(ncards, dtype='float64')

        na = np.zeros(ncards, dtype='int32')
        nd = np.zeros(ncards, dtype='int32')

        a20 = np.zeros(ncards, dtype='float64')
        a11 = np.zeros(ncards, dtype='float64')
        a02 = np.zeros(ncards, dtype='float64')
        d2 = np.zeros(ncards, dtype='float64')

        a30 = np.zeros(ncards, dtype='float64')
        a21 = np.zeros(ncards, dtype='float64')
        a12 = np.zeros(ncards, dtype='float64')
        a03 = np.zeros(ncards, dtype='float64')
        d3 = np.zeros(ncards, dtype='float64')

        a40 = np.zeros(ncards, dtype='float64')
        a31 = np.zeros(ncards, dtype='float64')
        a22 = np.zeros(ncards, dtype='float64')
        a13 = np.zeros(ncards, dtype='float64')
        a04 = np.zeros(ncards, dtype='float64')
        d4 = np.zeros(ncards, dtype='float64')

        a50 = np.zeros(ncards, dtype='float64')
        a41 = np.zeros(ncards, dtype='float64')
        a32 = np.zeros(ncards, dtype='float64')
        a23 = np.zeros(ncards, dtype='float64')
        a14 = np.zeros(ncards, dtype='float64')
        a05 = np.zeros(ncards, dtype='float64')
        d5 = np.zeros(ncards, dtype='float64')

        tab1 = np.zeros(ncards, dtype='int32')
        tab2 = np.zeros(ncards, dtype='int32')
        tab3 = np.zeros(ncards, dtype='int32')
        tab4 = np.zeros(ncards, dtype='int32')
        tabd = np.zeros(ncards, dtype='int32')

        for i, card in enumerate(self.cards):
            (mid, a10i, a01i, d1i, rhoi, avi, trefi, gei, nai, ndi, a20i, a11i,
             a02i, d2i, a30i, a21i, a12i, a03i, d3i, a40i,
             a31i, a22i, a13i, a04i, d4i, a50i, a41i,
             a32i, a23i, a14i, a05i, d5i,
             tab1i, tab2i, tab3i, tab4i, tabdi, comment) = card
            tab1i = tab1i if tab1i is not None else 0
            tab2i = tab2i if tab2i is not None else 0
            tab3i = tab3i if tab3i is not None else 0
            tab4i = tab4i if tab4i is not None else 0
            tabdi = tabdi if tabdi is not None else 0

            material_id[i] = mid
            a10[i] = a10i
            a01[i] = a01i
            d1[i] = d1i
            av[i] = avi
            na[i] = nai
            nd[i] = ndi
            a20[i] = a20i
            a11[i] = a11i
            a02[i] = a02i
            d2[i] = d2i
            a30[i] = a30i
            a21[i] = a21i
            a12[i] = a12i
            a03[i] = a03i
            d3[i] = d3i
            a40[i] = a40i
            a31[i] = a31i
            a22[i] = a22i
            a13[i] = a13i
            a04[i] = a04i
            d4[i] = d4i
            a50[i] = a50i
            a41[i] = a41i
            a32[i] = a32i
            a23[i] = a23i
            a14[i] = a14i
            a05[i] = a05i
            d5[i] = d5i
            rho[i] = rhoi
            tref[i] = trefi
            ge[i] = gei
            tab1[i] = tab1i
            tab2[i] = tab2i
            tab3[i] = tab3i
            tab4[i] = tab4i
            tabd[i] = tabdi
        self._save(material_id, a10, a01, d1, rho, av, tref, ge, na, nd, a20, a11,
                   a02, d2, a30, a21, a12, a03, d3, a40,
                   a31, a22, a13, a04, d4, a50, a41,
                   a32, a23, a14, a05, d5, tab1, tab2,
                   tab3, tab4, tabd)
        self.sort()
        self.cards = []

    def _save(self, material_id, a10, a01, d1, rho, av, tref, ge, na, nd, a20, a11,
              a02, d2, a30, a21, a12, a03, d3, a40,
              a31, a22, a13, a04, d4, a50, a41,
              a32, a23, a14, a05, d5, tab1, tab2,
              tab3, tab4, tabd):
        assert len(self.material_id) == 0, self.material_id
        self.material_id = material_id

        self.a10 = a10
        self.a01 = a01
        self.d1 = d1
        self.rho = rho
        self.av = av
        self.tref = tref
        self.ge = ge
        self.na = na
        self.nd = nd

        self.a20 = a20
        self.a11 = a11
        self.a02 = a02
        self.d2 = d2
        self.a30 = a30
        self.a21 = a21
        self.a12 = a12
        self.a03 = a03
        self.d3 = d3
        self.a40 = a40
        self.a31 = a31
        self.a22 = a22
        self.a13 = a13
        self.a04 = a04
        self.d4 = d4
        self.a50 = a50
        self.a41 = a41
        self.a32 = a32
        self.a23 = a23
        self.a14 = a14
        self.a05 = a05
        self.d5 = d5

        self.tab1 = tab1
        self.tab2 = tab2
        self.tab3 = tab3
        self.tab4 = tab4
        self.tabd = tabd
        assert len(self.material_id) > 0, self.material_id
        #self.model.log.warning('saved MATORT')

    def __apply_slice__(self, mat: MATHP, i: np.ndarray) -> None:
        mat.n = len(i)
        mat.material_id = self.material_id[i]

        mat.a10 = self.a10[i]
        mat.a01 = self.a01[i]
        mat.d1 = self.d1[i]
        mat.rho = self.rho[i]
        mat.av = self.av[i]
        mat.tref = self.tref[i]
        mat.ge = self.ge[i]
        mat.na = self.na[i]
        mat.nd = self.nd[i]

        mat.a20 = self.a20[i]
        mat.a11 = self.a11[i]
        mat.a02 = self.a02[i]
        mat.d2 = self.d2[i]
        mat.a30 = self.a30[i]
        mat.a21 = self.a21[i]
        mat.a12 = self.a12[i]
        mat.a03 = self.a03[i]
        mat.d3 = self.d3[i]
        mat.a40 = self.a40[i]
        mat.a31 = self.a31[i]
        mat.a22 = self.a22[i]
        mat.a13 = self.a13[i]
        mat.a04 = self.a04[i]
        mat.d4 = self.d4[i]
        mat.a50 = self.a50[i]
        mat.a41 = self.a41[i]
        mat.a32 = self.a32[i]
        mat.a23 = self.a23[i]
        mat.a14 = self.a14[i]
        mat.a05 = self.a05[i]
        mat.d5 = self.d5[i]

        mat.tab1 = self.tab1[i]
        mat.tab2 = self.tab2[i]
        mat.tab3 = self.tab3[i]
        mat.tab4 = self.tab4[i]
        mat.tabd = self.tabd[i]

    def geom_check(self, missing: dict[str, np.ndarray]):
        pass

    @parse_material_check
    def write_file(self, bdf_file: TextIOLike,
                   size: int=8, is_double: bool=False,
                   write_card_header: bool=False) -> None:
        max_int = self.material_id.max()
        print_card = get_print_card(size, max_int)
        for (mid, a10, a01, d1, rho, av, tref, ge,
             na, nd,
             a20, a11, a02, d2,
             a30, a21, a12, a03, d3,
             a40, a31, a22, a13, a04, d4,
             a50, a41, a32, a23, a14, a05, d5,
             tab1, tab2, tab3, tab4, tabd) in zip_longest(
                 self.material_id,
                 self.a10, self.a01, self.d1, self.rho, self.av, self.tref, self.ge,
                 self.na, self.nd,
                 self.a20, self.a11, self.a02, self.d2,
                 self.a30, self.a21, self.a12, self.a03, self.d3,
                 self.a40, self.a31, self.a22, self.a13, self.a04, self.d4,
                 self.a50, self.a41, self.a32, self.a23, self.a14, self.a05, self.d5,
                 self.tab1, self.tab2, self.tab3, self.tab4, self.tabd):

                #av = set_blank_if_default(self.av, 0.0)
                #na = set_blank_if_default(self.na, 0.0)
                #nd = set_blank_if_default(self.nd, 0.0)

                #a01 = set_blank_if_default(self.a01, 0.0)
                #a10 = set_blank_if_default(self.a10, 0.0)
                #d1 = set_blank_if_default(self.d1, 1000 * (self.a01 + self.a10))

                #a20 = set_blank_if_default(self.a20, 0.0)
                #a11 = set_blank_if_default(self.a11, 0.0)
                #a02 = set_blank_if_default(self.a02, 0.0)
                #d2 = set_blank_if_default(self.d2, 0.0)

                #a30 = set_blank_if_default(self.a30, 0.0)
                #a12 = set_blank_if_default(self.a12, 0.0)
                #a21 = set_blank_if_default(self.a21, 0.0)
                #a03 = set_blank_if_default(self.a03, 0.0)
                #d3 = set_blank_if_default(self.d3, 0.0)

                #a40 = set_blank_if_default(self.a40, 0.0)
                #a31 = set_blank_if_default(self.a31, 0.0)
                #a22 = set_blank_if_default(self.a22, 0.0)
                #a13 = set_blank_if_default(self.a13, 0.0)
                #a04 = set_blank_if_default(self.a04, 0.0)
                #d4 = set_blank_if_default(self.d4, 0.0)

                #a50 = set_blank_if_default(self.a50, 0.0)
                #a41 = set_blank_if_default(self.a41, 0.0)
                #a32 = set_blank_if_default(self.a32, 0.0)
                #a23 = set_blank_if_default(self.a23, 0.0)
                #a14 = set_blank_if_default(self.a14, 0.0)
                #a05 = set_blank_if_default(self.a05, 0.0)
                #d5 = set_blank_if_default(self.d5, 0.0)

                #tref = set_blank_if_default(self.tref, 0.0)
                #ge = set_blank_if_default(self.ge, 0.0)
                list_fields = ['MATHP', mid, a10, a01, d1, rho, av, tref, ge,
                               None, na, nd, None, None, None, None, None,
                               a20, a11, a02, d2, None, None, None, None,
                               a30, a21, a12, a03, d3, None, None, None,
                               a40, a31, a22, a13, a04, d4, None, None,
                               a50, a41, a32, a23, a14, a05, d5, None,
                               tab1, tab2, tab3, tab4, None, None, None, tabd]
                bdf_file.write(print_card(list_fields))
        return

