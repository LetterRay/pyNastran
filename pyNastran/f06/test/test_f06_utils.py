"""
tests:
 - plot sol_145
"""
import os
import unittest
from cpylog import get_logger2
#import  matplotlib
#matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt

#try:  # pragma: no cover
    #plt.figure()
    #plt.close()
#except:  # pragma: no cover
plt.switch_backend('Agg')

import pyNastran
from pyNastran.f06.utils import split_float_colons, split_int_colon
from pyNastran.f06.parse_flutter import plot_flutter_f06, make_flutter_plots

PKG_PATH = pyNastran.__path__[0]

class TestF06Utils(unittest.TestCase):
    def test_split_float_colon(self):
        """tests split_float_colon"""
        a = split_float_colons('1:')
        b = split_float_colons('1:5')
        c = split_float_colons(':4')

        assert a == [1.0, None], a
        assert b == [1.0, 5.0], b
        assert c == [None, 4.0], c
        with self.assertRaises(AssertionError):
            split_float_colons('1:5:2')

    def test_split_int_colon(self):
        """tests split_int_colon"""
        a = split_int_colon('1:5')
        assert a == [1, 2, 3, 4, 5], a

        b = split_int_colon('1:5:2')
        assert b == [1, 3, 5], b

        c = split_int_colon(':4')
        assert c == [0, 1, 2, 3, 4], c

        d = split_int_colon('1:5,10:15')
        assert d == [1, 2, 3, 4, 5, 10, 11, 12, 13, 14, 15], d

        d = split_int_colon('10:15,1:5')
        assert d == [1, 2, 3, 4, 5, 10, 11, 12, 13, 14, 15], d

    def test_plot_flutter(self):
        """tests plot_flutter_f06"""
        f06_filename = os.path.join(PKG_PATH, '..', 'models',
                                    'aero', 'bah_plane', 'bah_plane.f06')
        log = get_logger2(log=None, debug=None, encoding='utf-8')
        plot_flutter_f06(f06_filename, show=False, log=log)
        plt.close()

    def test_plot_flutter2(self):
        """tests plot_flutter_f06"""
        f06_filename = os.path.join(PKG_PATH, '..', 'models',
                                    'aero', '2_mode_flutter', '0012_flutter.f06')
        log = get_logger2(log=None, debug=None, encoding='utf-8')
        plot_flutter_f06(
            f06_filename, make_alt=True,
            modes=[2],
            plot_type='alt',
            f06_units='si', out_units='english_ft',
            plot_vg=True, plot_vg_vf=True, plot_root_locus=True,
            plot_kfreq_damping=True,
            show=False, log=log)
        plt.close()

        flutters = plot_flutter_f06(
            f06_filename,
            f06_units=None, out_units=None,
            plot_vg=True, plot_vg_vf=True, plot_root_locus=True,
            plot_kfreq_damping=True,
            export_f06_filename='nastran.f06',
            export_veas_filename='nastran.veas',
            export_zona_filename='zona.f06',
            vg_filename='vg_subcase_%i.png',
            vg_vf_filename='vg_vf_subcase_%i.png',
            kfreq_damping_filename='kfreq_damping_subcase_%i.png',
            root_locus_filename='root_locus_subcase_%i.png',
            show=False, log=log)
        plt.close()
        os.remove('vg_subcase_1.png')
        os.remove('vg_vf_subcase_1.png')
        os.remove('kfreq_damping_subcase_1.png')
        os.remove('root_locus_subcase_1.png')

        with self.assertRaises(NotImplementedError):
            plot_flutter_f06(
                f06_filename,
                plot_type='tas',
                f06_units='cat', out_units=None,
                plot_vg=True, plot_vg_vf=True, plot_root_locus=True,
                plot_kfreq_damping=True,
                show=False, log=log)
        with self.assertRaises(NotImplementedError):
            plot_flutter_f06(
                f06_filename,
                plot_type='density',
                f06_units='si', out_units='english_ft',
                plot_vg=True, plot_vg_vf=True, plot_root_locus=True,
                plot_kfreq_damping=True,
                show=True, log=log)

        #fluttersb = plot_flutter_f06(
            #f06_filename,
            #plot_type='alt',
            #f06_units='english_in', out_units='english_kt',
            #plot_vg=True, plot_vg_vf=True, plot_root_locus=True,
            #plot_kfreq_damping=True,
            #show=False, log=log)
        plot_flutter_f06(
            f06_filename,
            plot_type='rho',
            f06_units='si', out_units='english_ft',
            plot_vg=True, plot_vg_vf=True, plot_root_locus=True,
            plot_kfreq_damping=True,
            show=False, log=log)
        plt.close()

        plot_flutter_f06(
            f06_filename,
            plot_type='freq',
            f06_units='si', out_units='english_ft',
            plot_vg=True, plot_vg_vf=True, plot_root_locus=True,
            plot_kfreq_damping=True,
            show=False, clear=True, log=log)
        plt.close()

        plot_flutter_f06(
            f06_filename,
            plot_type='kfreq',
            f06_units='si', out_units='english_ft',
            plot_vg=True, plot_vg_vf=True, plot_root_locus=True,
            plot_kfreq_damping=True,
            show=False, clear=True, log=log)
        plt.close()

        plot_flutter_f06(
            f06_filename,
            plot_type='ikfreq',
            f06_units='si', out_units='english_ft',
            plot_vg=True, plot_vg_vf=True, plot_root_locus=True,
            plot_kfreq_damping=True,
            show=False, clear=True, log=log)
        plt.close()

        plot_flutter_f06(
            f06_filename,
            modes=[2],
            plot_type='damp',
            f06_units='si', out_units='english_ft',
            plot_vg=True, plot_vg_vf=True, plot_root_locus=True,
            plot_kfreq_damping=True,
            show=False, clear=True, log=log)
        plt.close()

        plot_type = 'eas'
        modes = None
        #xlim = [0., 500000.] # in/s
        xlim = None
        ylim_damping = [-0.2, 0.2]
        ylim_freq = None
        ylim_kfreq = None
        make_flutter_plots(modes, flutters, xlim, ylim_damping, ylim_freq, ylim_kfreq,
                           plot_type,
                           plot_vg=True, plot_vg_vf=True,
                           plot_root_locus=True, plot_kfreq_damping=True,
                           nopoints=True, noline=False,
                           #export_zona_filename=export_zona_filename,
                           #export_veas_filename=export_veas_filename,
                           #export_f06_filename=export_f06_filename,
                           #vg_filename=vg_filename,
                           #vg_vf_filename=vg_vf_filename,
                           #root_locus_filename=root_locus_filename,
                           #kfreq_damping_filename=kfreq_damping_filename,
                           show=False, clear=True)
        plt.close()
        os.remove('nastran.f06')
        os.remove('nastran.veas')
        os.remove('zona.f06')


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
