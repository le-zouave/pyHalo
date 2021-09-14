import numpy as np
from pyHalo.Halos.HaloModels.powerlaw import PowerLawSubhalo, PowerLawFieldHalo
from pyHalo.single_realization import Realization
import random

class RealizationExtensions(object):

    """
    This class supports operations that modify individual instances of the class Realization
    (see pyHalo.single_realization).
    """

    def __init__(self, realization):

        """

        :param realization: an instance of Realization
        """

        self._realization = realization

    def change_mass_definition(self, mdef, new_mdef, kwargs_new):

        kwargs_realization = self._realization._prof_params
        kwargs_realization.update(kwargs_new)
        halos = self._realization.halos
        new_halos = []

        if new_mdef == 'coreTNFW':
            from pyHalo.Halos.HaloModels.coreTNFW import coreTNFWSubhalo, coreTNFWFieldHalo
        else:
            raise Exception('changing to mass definition '+new_mdef + ' not implemented')

        for halo in halos:
            if halo.mdef == mdef:
                if halo.is_subhalo:
                    new_halo = coreTNFWSubhalo.fromTNFW(halo, kwargs_realization)
                else:
                    new_halo = coreTNFWFieldHalo.fromTNFW(halo, kwargs_realization)
                new_halos.append(new_halo)
            else:
                new_halos.append(halo)

        lens_cosmo = self._realization.lens_cosmo
        prof_params = self._realization._prof_params
        msheet_correction = self._realization._mass_sheet_correction
        rendering_classes = self._realization.rendering_classes
        rendering_center_x, rendering_center_y = self._realization.rendering_center

        return Realization.from_halos(new_halos, lens_cosmo, prof_params,
                                      msheet_correction, rendering_classes,
                                      rendering_center_x, rendering_center_y,
                                      self._realization.geometry)

    def core_collapse_by_mass(self, mass_ranges_subhalos, mass_ranges_field_halos,
                              probabilities_subhalos, probabilities_field_halos, kwargs_halo={}):

        """
        This routine transforms some fraction of subhalos and field halos into core collapsed profiles
        in the specified mass ranges

        :param mass_ranges_subhalos: a list of lists specifying the log10 halo mass ranges for subhalos
        e.g. mass_ranges_subhalos = [[6, 8], [8, 10]]
        :param mass_ranges_field_halos: a list of lists specifying the halo mass ranges for field halos
        e.g. mass_ranges_subhalos = [[6, 8], [8, 10]]
        :param probabilities_subhalos: a list of lists specifying the fraction of subhalos in each mass
        range that core collapse
        e.g. probabilities_subhalos = [0.5, 1.] makes half of subhalos with mass 10^6 - 10^8 collapse, and
        100% of subhalos with mass between 10^8 and 10^10 collapse
        :param probabilities_field_halos: same as probabilities subhalos, but for the population of field halos
        :param kwargs_halo: the keyword arguments for the collapsed halo profile
        :return: a new instance of Realization that includes the collapsed profiles
        """

        assert len(mass_ranges_subhalos) == len(probabilities_subhalos)
        assert len(mass_ranges_field_halos) == len(probabilities_field_halos)

        indexes = []

        for i_halo, halo in enumerate(self._realization.halos):
            u = np.random.rand()
            if halo.is_subhalo:
                for i, mrange in enumerate(mass_ranges_subhalos):
                    if halo.mass >= 10**mrange[0] and halo.mass < 10**mrange[1]:
                        if u <= probabilities_subhalos[i]:
                            indexes.append(i_halo)
                        break

            else:
                for i, mrange in enumerate(mass_ranges_field_halos):
                    if halo.mass >= 10**mrange[0] and halo.mass < 10**mrange[1]:
                        if u <= probabilities_field_halos[i]:
                            indexes.append(i_halo)
                        break

        return self.add_core_collapsed_halos(indexes, **kwargs_halo)

    def find_core_collapsed_halos(self, time_scale_function, velocity_dispersion_function,
                                  cross_section, t_sub=10., t_field=100., t_sub_range=2, t_field_range=2.,
                                  model_type='TCHANNEL'):

        """
        :param time_scale_function: a function that computes the characteristic timescale for SIDM halos. This function
        must take as an input the NFW halo density normalization, velocity dispersion, and cross section class,

        t_scale = time_scale_function(rhos, v_rms, cross_section_class)

        :param velocity_dispersion_function: a function that computes the central velocity disperion of the halo

        It must be callable as:
        v = velocity_dispersion_function(halo_mass, redshift, delta_c_over_c, model_type, additional_keyword_arguments)

        where model_type is a string (see for example the function solve_sigmav_with_interpolation in sidmpy.py)
        :param cross_section: the cross section class (see SIDMpy for examples)
        :param t_sub: sets the timescale for subhalo core collapse; subhalos collapse at t_sub * t_scale
        :param t_field: sets the timescale for field halo core collapse; field halos collapse at t_field * t_scale
        :param t_sub_range: halos begin to core collapse (probability = 0) at t_sub - t_sub_range, and all are core
        collapsed by t = t_sub + t_sub_range (probability = 1)
        :param t_field_range: field halos begin to core collapse (probability = 0) at t_field - t_field_range, and all
        are core collapsed by t = t_field + t_field_range (probability = 1)
        :param model_type: specifies the cross section model to use when computing the solution to the velocity
        dispersion of the halo
        :return: indexes of halos that are core collapsed
        """
        inds = []
        for i, halo in enumerate(self._realization.halos):

            if halo.mdef not in ['NFW', 'TNFW', 'coreTNFW']:
                continue

            concentration = halo.profile_args[0]
            rhos, rs = halo.params_physical['rhos'], halo.params_physical['rs']
            median_concentration = self._realization.lens_cosmo.NFW_concentration(halo.mass, halo.z, scatter=False)
            delta_c_over_c = 1 - concentration/median_concentration
            v_rms = velocity_dispersion_function(halo.mass, halo.z, delta_c_over_c, model_type, cross_section.kwargs)
            timescale = time_scale_function(rhos, v_rms, cross_section)

            if halo.is_subhalo:
                tcollapse_min = timescale * t_sub / t_sub_range
                tcollapse_max = timescale * t_sub * t_sub_range
            else:
                tcollapse_min = timescale * t_field / t_field_range
                tcollapse_max = timescale * t_field * t_field_range

            halo_age = self._realization.lens_cosmo.cosmo.halo_age(halo.z)

            if halo_age > tcollapse_max:
                p = 1.
            elif halo_age < tcollapse_min:
                p = 0.
            else:
                p = (halo_age - tcollapse_min) / (tcollapse_max - tcollapse_min)

            u = np.random.rand()
            if p >= u:
                inds.append(i)

        return inds

    def add_core_collapsed_halos(self, indexes, **kwargs_halo):

        """
        This function turns NFW halos in a realization into profiles modeled as PseudoJaffe profiles
        with 1/r^2 central density profiles with the same total mass as the original NFW
        profile.

        :param indexes: the indexes of halos in the realization to transform into PsuedoJaffe profiles
        :param kwargs_halo: the keyword arguments for the collapsed halo profile
        :return: A new instance of Realization where the halos indexed by indexes
        in the original realization have their mass definitions changed to PsuedoJaffe
        """

        halos = self._realization.halos
        new_halos = []

        for i, halo in enumerate(halos):

            if i in indexes:

                halo._args.update(kwargs_halo)
                if halo.is_subhalo:
                    new_halo = PowerLawSubhalo(halo.mass, halo.x, halo.y, halo.r3d, 'SPL_CORE',
                                                 halo.z, True, halo.lens_cosmo, halo._args, halo.unique_tag)
                else:
                    new_halo = PowerLawFieldHalo(halo.mass, halo.x, halo.y, halo.r3d, 'SPL_CORE',
                                                 halo.z, False, halo.lens_cosmo, halo._args, halo.unique_tag)
                new_halos.append(new_halo)

            else:
                new_halos.append(halo)

        lens_cosmo = self._realization.lens_cosmo
        prof_params = self._realization._prof_params
        msheet_correction = self._realization._mass_sheet_correction
        rendering_classes = self._realization.rendering_classes
        rendering_center_x, rendering_center_y = self._realization.rendering_center

        return Realization.from_halos(new_halos, lens_cosmo, prof_params,
                                      msheet_correction, rendering_classes,
                                      rendering_center_x, rendering_center_y,
                                      self._realization.geometry)

