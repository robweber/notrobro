from argparse import ArgumentParser
import os
import glob
import logging


def filter_videos(files):
    ext_list = ('.mp4', '.mkv', '.avi', '.mov', '.wmv')
    videos = list(filter(lambda f: os.path.splitext(f)[1] in ext_list, files))
    return videos

def find_missing(root, files):
    missing = []

    videos = filter_videos(files)

    suffix = '.edl'
    for f in videos:
        logging.debug('checking %s' % f)
        filename, _ = os.path.splitext(f)
        if((filename + suffix) not in files):
            missing.append(os.path.join(root,f))

    return missing

def main():
    argparse = ArgumentParser()
    argparse.add_argument('--path', '-p', type=str,
                          help='TV show directory path to check for edl files', required=True)
    argparse.add_argument('--log', '-l', type=str, choices=['info', 'debug'],
                          help='Run in debug mode', default='info')
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
        missing = missing + find_missing(root, files)

    logging.info('Missing edl files for:')
    for f in missing:
        logging.info(f)

if __name__ == '__main__':
    main()
