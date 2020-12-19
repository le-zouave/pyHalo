
def LOS_spatial_global(args):

    args_spatial = {}
    args_spatial['cone_opening_angle'] = args['cone_opening_angle']
    return args_spatial

def subhalo_spatial_uniform(args):

    args_spatial = {}
    args_spatial['rmax2d_arcsec'] = 0.5 * args['cone_opening_angle']
    return args_spatial

def subhalo_spatial_NFW(args, kpc_per_arcsec_zlens, zlens, lenscosmo):
    args_spatial = {}

    # EVERYTHING EXPRESSED IN KPC
    args_spatial['rmax2d'] = 0.5 * args['cone_opening_angle'] * kpc_per_arcsec_zlens

    if 'log_m_host' in args.keys():
        args['host_m200'] = 10 ** args['log_m_host']

    if 'host_m200' in args.keys():
        # EVERYTHING EXPRESSED IN KPC
        if args['host_m200'] < 100:
            raise Exception('you have specified a host halo mass less than 10 ** 2 solar masses... '
                            'probably not what you intended.')

        if 'parent_c' not in args.keys():
            args['parent_c'] = lenscosmo.NFW_concentration(args['host_m200'], zlens,
                  model='diemer19', mdef='200c', logmhm=0, scatter=True,
                 c_scale=60., c_power=-0.17, scatter_amplitude=0.13)

        if 'parent_Rs' not in args.keys():
            parent_Rs = lenscosmo.NFW_params_physical(args['host_m200'],
                                                            args['parent_c'], zlens)[1]

        parent_r200 = parent_Rs * args['parent_c']

        args_spatial['Rs'] = parent_Rs
        args_spatial['rmax3d'] = parent_r200
    else:
        try:
            args_spatial['Rs'] = args['parent_Rs']
            args_spatial['rmax3d'] = args['parent_r200']
        except:
            raise ValueError('must specify either (parent_c, host_m200, log_m_host) for parent halo, or '
                             '(parent_Rs, parent_r200) directly')

    if 'r_tidal' in args.keys():

        if isinstance(args['r_tidal'], str):
            if args['r_tidal'] == 'Rs':
                args_spatial['r_core_parent'] = args_spatial['Rs']
            else:
                if args['r_tidal'][-2:] != 'Rs':
                    raise ValueError('if specifying the tidal core radius as number*Rs, the last two '
                                     'letters in the string must be "Rs".')

                scale = float(args['r_tidal'][:-2])
                args_spatial['r_core_parent'] = scale * args_spatial['Rs']

        else:
            args_spatial['r_core_parent'] = args['r_tidal']

    return args_spatial
