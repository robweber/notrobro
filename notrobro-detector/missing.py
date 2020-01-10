from argparse import ArgumentParser
import os
import glob
import logging


def filter_videos(files):
    ext_list = ('.mp4', '.mkv', '.avi', '.mov', '.wmv')
    videos = list(filter(lambda f: os.path.splitext(f)[1] in ext_list, files))
    return videos

def read_exclude(path):
    result = []

    if(os.path.exists(os.path.join(path,'edl_exclude.txt'))):
        with open(os.path.join(path, 'edl_exclude.txt'), 'r') as f:
            result = f.readlines()

        result = list(map(lambda x: x.strip(), result))

    return result

def find_missing(root, files, exclude):
    missing = []

    # get a list of explicity excluded files along with all videos in the folder
    exclude_list = read_exclude(root)
    videos = filter_videos(files)

    suffix = '.edl'
    for f in videos:
        logging.debug('checking %s' % f)
        filename, _ = os.path.splitext(f)
        if((filename + suffix) not in files):
            missing.append({'file': os.path.join(root,f), 'exclude': (f in exclude_list)})

    if(len(missing) > 0 and exclude):
        generate_exclude(root, missing)

    return missing

def generate_exclude(root, files):
    logging.info('Generating exclude files %s' % root)

    with open(os.path.join(root, 'edl_exclude.txt'), 'w') as w:
        for f in files:
            w.write(os.path.basename(f['file']) + "\n")

def main():
    argparse = ArgumentParser()
    argparse.add_argument('--path', '-p', type=str,
                          help='TV show directory path to check for edl files', required=True)
    argparse.add_argument('--log', '-l', type=str, choices=['info', 'debug'],
                          help='Run in debug mode', default='info')
    argparse.add_argument('--gen-exclude', '-e', action='store_true', help='generate an exclude file for the detector based on the missing files')
    args = argparse.parse_args()

    # set the log level
    log_level = getattr(logging, args.log.upper())
    logging.basicConfig(format="%(levelname)s %(asctime)s %(threadName)s: %(message)s", level=log_level,
                        datefmt="%H:%M:%S")
    logging.debug('DEBUG logging enabled')

    if not os.path.exists(args.path):
        logging.info("TV show directory: " + args.path + " not found.")
        exit()
    else:
        if not os.path.isdir(args.path):
            logging.info("Path: " + args.path + " is not a directory.")
            exit()

    logging.info('Find missing EDL files')
    logging.info('Checking path: %s' % args.path)

    missing = []
    for root, dirs, files, in os.walk(args.path):
        missing = missing + find_missing(root, files, args.gen_exclude)

    if(len(missing) > 0):
        logging.info('Missing EDL files for:')
        for f in missing:
            if(f['exclude']):
                logging.info('%s (EXCLUDED)' % f['file'])
            else:
                logging.info(f['file'])
    else:
        logging.info('No missing EDL files in this path')

if __name__ == '__main__':
    main()
