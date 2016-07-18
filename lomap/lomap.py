r"""
LOMAP
=====

Alchemical free energy calculations hold increasing promise as an aid to drug 
discovery efforts. However, applications of these techniques in discovery 
projects have been relatively few, partly because of the difficulty of planning 
and setting up calculations. The Lead Optimization Mapper (LOMAP) is an 
automated algorithm to plan efficient relative free energy calculations between 
potential ligands within a substantial of compounds.

This is the user script.
"""

import mol
from logger import logger


def compute_similarity_matrix(mols, rules, nproc):
    """
    """

    scores = []
    N = len(mols)
    simmat = np.zeros(shape=(N,N), dtype=mol.MorphPair)

    if nproc > 1 or nproc <= 0:
        import multiprocessing as mp

        maxproc = mp.cpu_count()

        if nproc > maxproc:
            logger.warn('limitting number of processors to %i' % maxproc)
            nproc = maxproc
        elif nproc <= 0:
            nproc = maxproc

        pool = mp.Pool(nproc)
        map_func = pool.imap
    else:
        map_func = map

    for i in range(N-1):
        partial_func = partial(score, rules, mols[i])
        scores.append(map_func(partial_func, mols[i+1:N]) )

    for i, row in enumerate(scores):
        simmat[i][i+1:N] = [s for s in row]

    if parallel:
        pool.close()
        pool.join()

    return simmat

def read_molecules(files):
    """
    Read molecules from a list of files.
    
    :param files: files ontaining the molecule(s)
    :type files: list
    """

    all_mols = []

    for file in files:
        logger.info('Attempting to read %s' % file)
        mols = mol.read_molecules(file)

        if mols:
            all_mols.extend(mols)

    return all_mols

def setup_logger(logfile):
    """
    Setup for the logging facility.

    :param logfile: file to write to, if empty write to stdoug
    :type logfile: str
    """

    # FIXME: Do we want to tee? -> add stream handler to logger
    #        Do we want to have different logs to file and stdout/stderr?
    #          -> separate loggers or use just prints?
    if opts.logfile:
        hdlr = logging.FileHandler(opts.logfile)
        hdlr.setFormatter(LogFormatter())
        logger.addHandler(hdlr)
        logger.setLevel(logging.INFO)
    else:
        hdlr = logging.StreamHandler(sys.stdout)
        hdlr.setFormatter(LogFormatter())
        logger.addHandler(hdlr)


if __name__ == '__main__':
    import sys
    import argparse
    import logging
    
    from logger import LogFormatter


    parser = argparse.ArgumentParser(description=
        'Lead Optimization Mapper 2. A program to plan alchemical relative '
        'binding affinity calculations.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('molfiles', nargs='+',
                        help='Files containing molecules')
    parser.add_argument('-t', '--time', default=20, metavar='N', type=int,
                        help='Set the maximum time in seconds to perform the '
                        'mcs search between pair of molecules')
    parser.add_argument('-np', '--nproc', metavar='N', default=1, type=int,
                        help='Parallel mode: If an integer number N '
                        'is specified, N processes will be executed to build '
                        'the similarity matrices. The maximum numer of '
                        'processors will be used if N<=0 or N exceeds the '
                        'number of processors.')
    parser.add_argument('-v', '--verbose', default='info', type=str,
                        choices=['off', 'info', 'pedantic'],
                        help='verbose mode selection')
    parser.add_argument('-l', '--logfile', default='', type=str,
                        help='File for logging information')

    out_group = parser.add_argument_group('Output settings')
    out_group.add_argument('-o', '--output', default=True, action='store_true',
                           help='Generates output files')
    out_group.add_argument('-n', '--name', type=str, default='out',
                           help='File name prefix used to generate the output '
                           'files')

    parser.add_argument('-d', '--display', default=False, action='store_true',
                        help='Display the generated graph by using Matplotlib')

    graph_group = parser.add_argument_group('Graph settings')
    graph_group.add_argument('-m', '--max', default=6, type=int,
                             help='The maximum distance used to cluster the '
                             'graph nodes')
    graph_group.add_argument('-c', '--cutoff', metavar='C', default=0.4,
                             type=float,
                             help='The Minimum Similariry Score (MSS) used to '
                             'build the graph')

    opts = parser.parse_args()

    setup_logger(opts.logfile)

    all_mols = read_molecules(opts.molfiles)

    if not all_mols:
        logger.error('No molecular structures found in input file(s)')
        sys.exit(1)

    rules = []
    simmat = compute_similarity_matrix(all_mols, rules, opts.nproc)

