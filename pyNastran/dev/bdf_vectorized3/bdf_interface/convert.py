import inspect
from pyNastran.dev.bdf_vectorized3.bdf import BDF


def convert(model: BDF, units_to: list[str], units: list[str]) -> None:
    xyz_scale = 2.0
    mass_scale = 3.0
    time_scale = 1.0
    gravity_scale = 1.0
    temperature_scale = 1.0

    area_scale = xyz_scale ** 2
    volume_scale = xyz_scale ** 3
    force_scale = mass_scale * gravity_scale * xyz_scale / time_scale ** 2
    moment_scale = force_scale * xyz_scale
    velocity_scale = xyz_scale / time_scale
    accel_scale = xyz_scale / time_scale ** 2
    area_inertia_scale = xyz_scale ** 4
    mass_inertia_scale = mass_scale * xyz_scale ** 2
    alpha_scale = temperature_scale / time_scale

    density_scale = force_scale / volume_scale
    pressure_scale = force_scale / area_scale
    stress_scale = force_scale / area_scale

    stiffness_scale = stress_scale  # E, G
    #linear_stiffness_scale = force_scale / xyz_scale  #F/x = kt
    #rotational_stiffness_scale = moment_scale  #M/theta = kr

    scales_dict = {
        'xyz_scale': xyz_scale,
        'area_scale': area_scale,
        'volume_scale': volume_scale,

        'time_scale': time_scale,
        'gravity_scale': gravity_scale,
        'mass_scale': mass_scale,
        'temperature_scale': temperature_scale,
        'alpha_scale': alpha_scale,

        'velocity_scale': velocity_scale,
        'accel_scale': accel_scale,
        'force_scale': force_scale,
        'moment_scale': moment_scale,
        'pressure_scale': pressure_scale,

        'density_scale': density_scale,
        'mass_inertia_scale': mass_inertia_scale,
        'area_inertia_scale': area_inertia_scale,
        'nsm_per_length_scale': mass_scale / xyz_scale,
        'nsm_per_area_scale': mass_scale / area_scale,

        'stress_scale': stress_scale,
        'stiffness_scale': stiffness_scale,

    }
    CARDS_TO_SKIP = {
        'SPOINT', 'EPOINT', 'CTUBE', 'CROD',
        'SET1', 'ASET', 'BSET', 'CSET', 'OMIT', 'USET', 'SUPORT',
        'PLOTEL', 'SPCADD', 'MPCADD', 'DCONADD',
        'CQUAD', 'CTETRA', 'CPYRAM', 'CPENTA', 'CHEXA', 'PSOLID', 'PLSOLID',
        'LOAD', 'DLOAD',
    }
    SUPPORTED_CARDS = {
        'GRID',  'POINT', 'CONM1', 'CONM2',
        'CBAR', 'PBAR', 'PBARL',
        'CBEAM', 'PBEAM', 'PBEAML',
        'PROD', 'PTUBE', 'CONROD',
        'RBE1', 'RBE2', 'RBE3', 'RBAR', 'RBAR1', 'RROD',
        'CTRIA3', 'CQUAD4', 'CTRIAR', 'CQUADR', 'CTRIA6', 'CQUAD8',
        'PSHELL', 'PCOMP', 'PCOMPG', 'PLPLANE',
        'PCOMPS', 'PCOMPLS',
        'MAT1', 'MAT2', 'MAT8', 'MAT9', 'MAT10', 'MAT10C',
        'PLOAD', 'PLOAD1', 'PLOAD2', 'PLOAD4',
    }
    cards = [card for card in model._cards_to_setup
             if card.n and card.type not in CARDS_TO_SKIP]
    skipped_cards = []
    for card in cards:
        if card.type in SUPPORTED_CARDS:
            sig = inspect.signature(card.convert)
            for key in sig._parameters:
                assert key == 'kwargs' or key in scales_dict, f'card={card.type!r} key={key!r}'
            #print(card.type)
            card.convert(**scales_dict)
        elif hasattr(card, 'convert'):  # pragma: no cover
            raise RuntimeError(card.type)
            card.convert(**scales_dict)
        else:
            skipped_cards.append(card.type)
    if skipped_cards:
        model.log.warning(f'cant convert {skipped_cards}')

