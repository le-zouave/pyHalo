from pyHalo.Rendering.Field.base import LineOfSightBase
import numpy as np
from pyHalo.defaults import *

class DeltaBase(LineOfSightBase):

    def __init__(self, halo_mass_function_class, geometry_class, rendering_args, spatial_parameterization, minimum_mass,
                 lens_plane_redshifts, delta_zs):

        self._minimum_mass = minimum_mass

        self._zlens = halo_mass_function_class.geometry._zlens

        self.lens_plane_redshifts, self.delta_zs = lens_plane_redshifts, delta_zs

        super(DeltaBase, self).__init__(halo_mass_function_class, geometry_class, rendering_args, spatial_parameterization,
                                        lens_plane_redshifts, delta_zs)

    def negative_kappa_sheets_theory(self):

        kwargs_mass_sheets = self.keys_convergence_sheets
        logM, mass_fraction = kwargs_mass_sheets['logM_delta'], kwargs_mass_sheets['mass_fraction']

        kappa_scale = kwargs_mass_sheets['kappa_scale']

        kwargs_out = []
        redshifts = []
        profile_names_out = []

        M = 10**logM

        lens_plane_redshifts_half = self.lens_plane_redshifts[0::2]
        delta_zs_double = 2 * self.delta_zs[0::2]

        for z, delta_z in zip(lens_plane_redshifts_half, delta_zs_double):

            if z < kwargs_mass_sheets['zmin']:
                continue
            if z > kwargs_mass_sheets['zmax']:
                continue

            n_objects = self.normalization(z, delta_z, M, mass_fraction, self.geometry._zlens,
                                      self.halo_mass_function, self.rendering_args,
                                     None)
            area = self.geometry.angle_to_physical_area(0.5 * self.geometry.cone_opening_angle, z)
            kappa_theory = kappa_scale * n_objects * M / self.lens_cosmo.sigma_crit_mass(z, area)

            if kappa_theory > 0:
                kwargs_out.append({'kappa_ext': -kappa_theory})
                redshifts.append(z)
                profile_names_out += ['CONVERGENCE']

        return kwargs_out, profile_names_out, redshifts

    @property
    def keys_convergence_sheets(self):

        args_convergence_sheets = {}
        required_keys = ['logM_delta', 'mass_fraction', 'kappa_scale', 'zmin', 'zmax']

        for key in required_keys:
            if key not in self.rendering_args.keys():
                raise Exception('When specifying mass function type DELTA, must provide '
                                'key word arguments logM_delta and mass_fraction.')

            args_convergence_sheets[key] = self.rendering_args[key]

        return args_convergence_sheets

    @staticmethod
    def keyword_parse(kwargs, lensing_mass_func):

        args_mfunc = {}
        required_keys = ['zmin', 'zmax', 'logM_delta', 'mass_fraction',
                         'LOS_normalization', 'parent_m200', 'kappa_scale',
                         'draw_poisson']

        for key in required_keys:

            if key == 'LOS_normalization':

                if key in kwargs.keys():
                    args_mfunc['LOS_normalization'] = kwargs[key]
                else:
                    args_mfunc['LOS_normalization'] = 1
                continue

            try:
                args_mfunc[key] = kwargs[key]
            except:
                if key == 'zmin':
                    args_mfunc['zmin'] = lenscone_default.default_zstart
                else:
                    args_mfunc['zmax'] = lensing_mass_func.geometry._zsource - lenscone_default.default_zstart

        return args_mfunc

    def render_masses(self, zi, delta_zi, aperture_radius):

        object_mass = 10 ** self.rendering_args['logM_delta']

        if object_mass < self._minimum_mass:
            component_fraction = 0.
        else:
            component_fraction = self.rendering_args['mass_fraction']

        nobjects = self.normalization(zi, delta_zi, object_mass, component_fraction,
                                      self._zlens, self.halo_mass_function, self.rendering_args,
                                      aperture_radius)

        nobjects = np.random.poisson(nobjects)

        m = np.array([object_mass] * nobjects)

        return m

    def normalization(self, z, delta_z, mass, mass_fraction, zlens, lensing_mass_function_class, rendering_args,
                                     aperture_radius):

        volume_element_comoving = self.geometry.volume_element_comoving(z, delta_z, aperture_radius)

        boost = self.two_halo_boost(z, delta_z, rendering_args['parent_m200'], zlens, lensing_mass_function_class)

        rho_dV = lensing_mass_function_class.component_density(z,
            mass_fraction
        )

        n = rho_dV * volume_element_comoving * boost * rendering_args['LOS_normalization']/mass

        return n
