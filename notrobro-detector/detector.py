from argparse import ArgumentParser
from abc import ABC, abstractmethod
import signal
import sys
import os
import glob
import imagehash
from PIL import Image
import subprocess
import shutil
import copy


class DetectorMethod(ABC):

    @abstractmethod
    def get_common_intro(self, l1, l2):
        pass

    @abstractmethod
    def get_common_outro(self, l1, l2):
        pass

class AllMethods(DetectorMethod):
    methods = []

    def __init__(self):
        self.methods.append(AllMatchMethod())
        self.methods.append(LongestContinousMethod())


    def get_common_intro(self, l1, l2):
        result = []
        i = 0
        while(i < len(self.methods) and len(result) == 0):
            result = self.methods[i].get_common_intro(l1,l2)
            i = i + 1

        return result

    def get_common_outro(self, l1, l2):
        result = []
        i = 0
        while(i < len(self.methods) and len(result) == 0):
            result = self.methods[i].get_common_outro(l1,l2)
            i = i + 1

        return result

class AllMatchMethod(DetectorMethod):

    def get_common_intro(self, l1, l2):
        common = []
        for i, element in enumerate(l1):
            try:
                ind = l2.index(element)
                common.append((i, ind))
            except:
                pass
        return common

    def get_common_outro(self, l1, l2):
        common = []
        for i, element1 in enumerate(l1):
            for j, element2 in enumerate(l2):
                if (element1-element2) <= 5:
                    if len(common) != 0 and common[-1][1] < j:
                        common.append((i, j))
                        break
                    elif len(common) == 0:
                        common.append((i, j))
                        break
        return common


class LongestContinousMethod(DetectorMethod):

    def get_common_intro(self, l1, l2):
        subarray = []
        indices = []
        len1, len2 = len(l1), len(l2)
        for i in range(len1):
            for j in range(len2):
                temp = 0
                cur_array = []
                cur_indices = []
                # hamming distance
                while ((i+temp < len1) and (j+temp < len2) and (l1[i+temp]-l2[j+temp]) <= 30):
                    cur_array.append(l2[j+temp])
                    cur_indices.append((i+temp, j+temp))
                    temp += 1
                if (len(cur_array) > len(subarray)):
                    subarray = cur_array
                    indices = cur_indices
        # return subarray, indices
        return indices

    def get_common_outro(self, l1, l2):
        # not implemented for this method yet
        return []

class Detector:
    jpg_folder = './jpgs'  # location location of jpg images from video
    threshold = 0.35  # default threshold, can be passed as arg
    method = None  # detector method class
    debug = False


    def  __init__(self, threshold, method, debug=False):
        self.threshold = threshold
        self.debug = debug

        if(method == 'all_match'):
            self.method = AllMatchMethod()
        elif(method == 'longest_common'):
            self.method = LongestContinousMethod()
        elif(method == 'all'):
            self.method = AllMethods()


    def get_hash(self, path):
        return imagehash.phash(Image.open(path))


    def get_hash_from_dir(self, path):
        images = os.listdir(path)
        images.sort()
        hashlist = []
        for img in images:
            hashlist.append(self.get_hash(os.path.join(path, img)))
        return hashlist, images


    def get_timings(self, out, category):
        to_find = "pts_time:"
        length = len(to_find)
        loc = -1
        times = []
        while True:
            loc = out.find(to_find, loc + 1)
            if loc == -1:
                break
            time = ""
            current = loc + length
            while out[current] != " ":
                time += out[current]
                current += 1
            times.append(float(time))
        if category is "intro":
            del times[-1]
        return times


    def generate_timestring(self, start, end, action):
        time_string = "%f %f %d" % (start, end, action)

        return time_string


    def get_duration(self, out):
        to_find = "Duration: "
        length = len(to_find)
        loc = out.find(to_find, 0)
        duration = ""
        current = loc + length
        while out[current] != ",":
            duration += out[current]
            current += 1
        total = duration.split(":")
        to_sec = float(total[0])*3600.0 + float(total[1])*60.0 + float(total[1])
        return to_sec


    def get_scene_transitions(self, path, category):
        th = self.threshold
        end_time = 360  # in seconds (can be put in arguments as well)
        # in seconds from end of video (can be put in arguments as well)
        outro_end_time = -300

        name, _ = os.path.splitext(path)
        name = os.path.join(self.jpg_folder, os.path.basename(name))
        if os.path.exists(name):
            shutil.rmtree(name)
        os.mkdir(name)

        input_file = path

        if category is "intro":
            scenes = "ffmpeg -i " + '"' + input_file + '"' + " -ss 0 -to " + \
                str(end_time) + ' -vf  "select=' + "'gt(scene," + str(th) + ")'," + \
                'showinfo" -vsync vfr "' + name + '/' + '"%04d.jpg>scenes 2>&1'
        elif category is "outro":
            scenes = "ffmpeg -sseof " + str(outro_end_time) + " -i " + '"' + input_file + '"' + ' -vf  "select=' + \
                "'gt(scene," + str(th) + ")'," + 'showinfo" -vsync vfr "' + \
                   name + '/' + '"%04d.jpg>scenes 2>&1'

        subprocess.call(scenes, shell=True)

        file = open("scenes", "r")
        out = file.read()
        file.close()
        times = self.get_timings(out, category)

        os.remove("./scenes")

        return times


    def get_hash_video(self, path, category):
        scene_transitions = self.get_scene_transitions(path, category)
        if category == "outro":
            duration = "ffmpeg -i " + '"' + path + '"' + ">duration 2>&1"
            subprocess.call(duration, shell=True)
            file = open("duration", "r")
            out = file.read()
            file.close()
            total_time = self.get_duration(out)
            os.remove("./duration")
            outro_end_time = -300
            begin = total_time + outro_end_time
            for i in range(len(scene_transitions)):
                scene_transitions[i] = scene_transitions[i] + begin
        name, _ = os.path.splitext(path)
        name = os.path.join(self.jpg_folder, os.path.basename(name))
        hashlist, _ = self.get_hash_from_dir(name)
        if os.path.exists(name) and not self.debug:
            shutil.rmtree(name)

        return hashlist, scene_transitions


    def gen_timings_processed(self, videos_process):
        result = {}  # dict containing path: {intro,outro} information

        # Processing for Intros
        print("Finding Intros")
        print("\t%s" % videos_process[0])

        video_prev = videos_process[0]
        result[video_prev] = {}
        hash_prev, scene_prev = self.get_hash_video(
            videos_process[0], "intro")

        for i in range(1, len(videos_process)):
            print("\t%s" % videos_process[i])
            result[videos_process[i]] = {}

            hash_cur, scene_cur = self.get_hash_video(
                videos_process[i], "intro")
            indices = self.method.get_common_intro(hash_prev, hash_cur)

            if(len(indices) > 0):
                intro_start_prev = scene_prev[indices[0][0]]
                intro_start_cur = scene_cur[indices[0][1]]

                intro_end_prev = scene_prev[indices[-1][0] + 1]
                intro_end_cur = scene_cur[indices[-1][1] + 1]

                # generate cut in edl files (4=intro)
                if 'intro' not in result[video_prev]:
                    result[video_prev]['intro'] = self.generate_timestring(intro_start_prev, intro_end_prev, 4)

                result[videos_process[i]]['intro'] = self.generate_timestring(intro_start_cur, intro_end_cur, 4)
            else:
                print('\tNo intro found %s : %s' % (video_prev, videos_process[i]))

            video_prev = videos_process[i]
            hash_prev = hash_cur
            scene_prev = scene_cur

        # Processing for Outros
        print('Finding Outros')
        print('\t%s' % videos_process[0])

        video_prev = videos_process[0]
        hash_prev, scene_prev = self.get_hash_video(
            videos_process[0], "outro")

        for i in range(1, len(videos_process)):
            print('\t%s' % videos_process[i])
            hash_cur, scene_cur = self.get_hash_video(
                videos_process[i], "outro")
            indices = self.method.get_common_outro(hash_prev, hash_cur)

            if(len(indices) > 0):
                outro_start_prev = scene_prev[indices[0][0]]
                outro_start_cur = scene_cur[indices[0][1]]

                try:
                    outro_end_prev = scene_prev[indices[-1][0] + 1]
                except:
                    outro_end_prev = scene_prev[indices[-1][0]]

                try:
                    outro_end_cur = scene_cur[indices[-1][1] + 1]
                except:
                    outro_end_cur = scene_cur[indices[-1][1]]

                # generate cut in edl file (5=outro)
                if 'outro' not in result[video_prev]:
                    result[video_prev]['outro'] = self.generate_timestring(outro_start_prev, outro_end_prev, 5)

                result[videos_process[i]]['outro'] = self.generate_timestring(outro_start_cur, outro_end_cur, 5)
            else:
                print('\tNo outro found %s : %s' % (video_prev, videos_process[i]))

            video_prev = videos_process[i]
            hash_prev = hash_cur
            scene_prev = scene_cur

        return result


    def create_edl(self, timings):
        for file in timings.keys():
            filename, _ = os.path.splitext(file)
            suffix = '.edl'
            edl_file = filename + suffix

            # only write the file if a timing exists for this video
            if('intro' in timings[file] or 'outro' in timings[file]):
                with open(edl_file, 'w') as f:
                    if 'intro' in timings[file]:
                        f.write(timings[file]['intro'] + "\n")
                    if 'outro' in timings[file]:
                        f.write(timings[file]['outro'] + "\n")


    def generate(self, path, force):
        files = os.listdir(path)
        all_files = [os.path.join(path, i) for i in files]

        # get the video files
        videos = []
        for ext in ('*.mp4', '*.mkv', '*.avi', '*.mov', '*.wmv'):  # video formats - extendable
            videos.extend(glob.glob(os.path.join(path, ext)))

        # if there is only 1 video in the directory
        if len(videos) == 1:
            print("Add atleast 1 more video of the TV show to the directory for processing.")
            exit()

        if(not os.path.exists(self.jpg_folder)):
            os.mkdir(self.jpg_folder)

        # get videos which don't have a skip timings file (currently edl) according to --force parameter
        videos_process = []
        if force is False:
            for file in videos:
                filename, _ = os.path.splitext(file)
                suffix = '.edl'
                if (filename + suffix) not in all_files:
                    videos_process.append(file)
        else:
            videos_process = copy.deepcopy(videos)

        if len(videos_process) == 0:
            print("No videos to process.")
            exit()
        elif len(videos_process) == 1:
            vid = videos_process[0]
            videos.sort()  # basic ordering for videos by sorting based on season and episode
            try:
                comp_vid = videos[videos.index(vid) - 1]
            except:
                comp_vid = videos[videos.index(vid) + 1]
            timings = self.gen_timings_processed(
                [comp_vid, vid])
            self.create_edl(timings)
        else:
            videos_process.sort()  # basic ordering for videos by sorting based on season and episode
            timings = self.gen_timings_processed(
                videos_process)
            self.create_edl(timings)

        if(not self.debug):
            shutil.rmtree(self.jpg_folder)

        print("Timing files created.")


def signal_handler(sig, frame):
        print('You pressed Ctrl+C!')
        sys.exit(0)


def main():
    argparse = ArgumentParser()
    argparse.add_argument('--path', '-p', type=str,
                          help='TV show directory path')
    argparse.add_argument('--threshold', '-t', type=str,
                          help='Threshold for scene change detection(default=0.35)', default='0.35')
    argparse.add_argument('--method', '-m', type=str,
                          help='Method used for timings generation (all, all_match, or longest_common). "all" method will run every method until a match is found or no methods are left to try', default='all')
    argparse.add_argument('--force', '-f', action='store_true',
                          help='Process all videos in the directory')
    argparse.add_argument('--debug', '-d', action='store_true',
                          help='Run in debug mode, keeps temp files for analysis')
    args = argparse.parse_args()
    signal.signal(signal.SIGINT, signal_handler)

    if args.path is None:
        print("Enter a directory path.")
        exit()
    else:
        if not os.path.exists(args.path):
            print("TV show directory: " + args.path + " not found.")
            exit()
        else:
            if not os.path.isdir(args.path):
                print("Path: " + args.path + " is not a directory.")
                exit()

    if args.method not in ["all_match", "longest_common", "all"]:
        print("Enter correct method: (1) all (2) all_match or (3) longest_common")
        exit()

    print('Threshold: %s' % args.threshold)
    print('Method: %s' % args.method)
    detector = Detector(args.threshold, args.method, args.debug)
    detector.generate(args.path, args.force)


if __name__ == '__main__':
    main()
