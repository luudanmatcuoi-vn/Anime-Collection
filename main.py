import os, sys, json, ffmpeg, anitopy, textdistance, config, logging, requests, re, time, csv
from os import listdir, system
from os.path import isfile, isdir, join, getsize
from imohash import hashfile
from mal import AnimeSearch, Anime
from datetime import date, datetime
from database import add_entry, get_sheet_data, create_change_sheet, push

# Load Config và tạo logging
cfg = config.Config('config.ini')
logging.basicConfig(filename='logging.log',level=logging.INFO )
# set up logging to console
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)

logging.info("Newrun------------------------------------------------------------------------------- "+str(datetime.now()))

# Lấy MAL API token
f = open("token.json","r")
token = json.loads(f.read())
f.close()
##################################
# Hàm khám phá tất cả media trong folder rootpath

def explore_path(path, files = []):
    #Add files from this folder
    fi =[]
    try:
        for f in listdir(path):
            if isfile(join(path,f)) and ("mkv" in f[-4:].lower() or "mp4" in f[-4:].lower() ):
                fi+=[f]
    except:
        logging.error(f"Folder {path} can't explore. Please check again")

    files = []
    for f in fi:
        files = files + [ {'filename':f , 'path':path, 'size':getsize(join(path,f))} ]
    #Scan subfolders
    try:
        fo = [f for f in listdir(path) if not isfile(join(path,f)) ]
    except:
        logging.error(f"Subfolder {path} can't explore. Please check again")
        fo=[]

    fo.sort()
    for folder in fo:
        # sys.stdout.write("\rScan folder: "+join(path,folder)+" "*(150-len(path)))
        # sys.stdout.flush()
        logging.info( "Scan folder: "+join(path,folder) )
        files += explore_path(join(path,folder))
    return files

def hash_files(file_list):
    for file in file_list:
        file["hash"] = hashfile( join(file["path"],file["filename"] ), hexdigest=True)
    return file_list

# Tạo ra prediction của 1 file bất kỳ dựa vào filename
def add_file(filename, filepath):
    # tìm name, eps
    temp = anitopy.parse(filename, options = cfg["anitopy_options"])
    if "release_group" not in temp.keys(): temp["release_group"] = ""

    if "anime_title" in temp.keys():

        # Xử lý episode_number
        if "episode_number" not in temp.keys(): temp["episode_number"] = 0
        try:
            eps = float(temp["episode_number"])
        except:
            if temp["anime_title"][-1] in [str(g) for g in range(10)] and "s" not in temp["anime_title"][-4:].lower():
                eps = re.findall("[0-9\.]+",temp["anime_title"][-4:])
                temp["anime_title"] = "".join( temp["anime_title"].rsplit(eps[0], 1) )
                eps = float(eps[0])
            else:
                eps = 0
            eps = float(eps)
        finally:
            eps = eps//1

        result = { "filename": temp["file_name"],
            "path": filepath,
            "name": temp["anime_title"],
            "episodes": str(eps),
            "fansub": temp["release_group"],
            "file_extension": temp["file_extension"],
            "warning": 0
            }
    else:
        logging.error("File {} can't parse name. (5)".format(filename))
        result = { "filename": temp["file_name"],
            "path": filepath,
            "name": "",
            "episodes": 0,
            "fansub": "",
            "file_extension": temp["file_extension"],
            "warning": 5
            }

    # tìm duration
    temp = metadata(filepath+"\\"+filename)
    result.update(temp)

    # tạo ra prediction
    temp = search_mal(name = result["name"], eps = result["episodes"], duration = result["duration"] , parrent = filepath )

    result.update(temp) # Cập nhật thêm title và mal_id prediction
    return result
    
# Hàm lấy metadata của 1 file ==> Trả kết quả
def metadata(filepath):
    vid = ffmpeg.probe(filepath)
    metavid = [f for f in vid['streams'] if f['codec_type'] == 'video'][0]
    result={}
    result["width"] = metavid["width"]
    result["height"] = metavid["height"]
    result["duration"]= int(float(vid["format"]["duration"]))
    # result["bitrate"]=vid["format"]["bit_rate"]
    # result["softsub"] = bool([f for f in vid['streams'] if f['codec_type'] == 'subtitle'])
    return result

# Hàm search AniID
def get_anime_info_by_name(name):
    try:
        search = AnimeSearch(name)
    except:
        logging.error("{} can't search using MAL API".format(name))
        return False
    # Lấy title, mal_id và episodes vào res
    res = [{"title":search.results[i].title , "mal_id":search.results[i].mal_id , "episodes":search.results[i].episodes}  for i in range(cfg["search_mal_numbers"])]
    
    # Lấy duration
    def req_Ani():
        for i in range(len(res)):
            Ani = requests.get("https://api.myanimelist.net/v2/anime/"+str(res[i]["mal_id"])+"?fields=title,alternative_titles,average_episode_duration", headers={"Authorization":"Bearer "+token["access_token"]} )
            if Ani.status_code == 200:
                logging.debug("Ani text: "+Ani.text)
                Ani = json.loads(Ani.text)
            elif Ani.status_code==403 and "There might be too much traffic or a configuration error." in Ani.text:
                logging.warning("MAL API got 403 error: "+Ani.text)
                time.sleep(60)
                req_Ani()
                return True
            else:
                logging.error("Can't connect to MAL API: "+Ani.text)
                Ani = {"title": res[i]["title"], "average_episode_duration": 0, "alternative_titles":{} }
            res[i]["duration"] = int( Ani["average_episode_duration"] or 0 )
            res[i]["alternative_titles"] = Ani["alternative_titles"]
    req_Ani()

    # Ghi thêm dữ liệu vào file search_mal.dat
    with open('search_mal.dat', 'a', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        write = json.dumps( res , ensure_ascii=False)
        writer.writerow(  [name,str(date.today())]+[write] )
    return res

# Hàm search AniID
def search_mal(name, eps=0, duration=0, parrent = ""):
    logging.debug("search_mal "+name)

    # Kiểm tra đã tìm anime bằng tên đó chưa
    try:
        with open('search_mal.dat', newline='') as f:
            temp = csv.reader(f, delimiter=';')
            for t in temp:
                if name == t[0]:
                    temp = json.loads(t[2])
                    break
            if type(temp) != type([]):
                raise Exception("No search_mal found on data") 
    except:
        temp = get_anime_info_by_name(name)

    if not temp:
        logging.error("Can't search_mal")
        temp = {"title": "", "mal_id":0, "point": -100, "warning": 2}
        return temp

    for i in range(len(temp)):
        temp[i]["point"] = (cfg["search_mal_numbers"]-i)*3

        ### title and name distance
        distance = textdistance.hamming(temp[i]["title"], name)
        for tit in temp[i]["alternative_titles"].keys():
            temp_distance = textdistance.hamming(temp[i]["alternative_titles"][tit], name)
            if temp_distance<distance: distance = temp_distance
        temp[i]["point"] -= distance

        ### Duration
        # Nếu delta duration nhỏ hơn config và duration ko phải movie hoặc nếu là movie thì cả 2 phải lớn hơn 3600s
        if (abs(duration-temp[i]["duration"])< cfg["duration_delta"]*60 and duration < 3600) or (temp[i]["duration"] and duration>3600):
            temp[i]["point"] += 100
        else:
            temp[i]["point"] -= 100

        ### eps
        if float(eps)==0.0:
            pass
        elif float(eps) <= int( temp[i]["episodes"] or 0):
            temp[i]["point"] +=100
        else:
            temp[i]["point"] -=100
    
    # Kiểm tra point có lớn hơn 0 ko. Nếu không, tìm theo parrent folder
    temp = max(temp, key = lambda x:x["point"])
    if temp["point"]<0:
        logging.warning("search_mal : {} result: {} point: {}".format(name,temp["title"], temp["point"] ) )
        temp = {"title": "", "mal_id":0, "episodes": 0, "point": -100, "duration":0, "warning": 2}

    # Trước khi trả kết quả phải xóa duration, eps đề phòng xung đột
    temp.pop("duration")
    temp.pop("episodes")

    return temp
    # return kết quả object {title, titleJP, mal_id, episodes, point}

def commit_folder(path):
    files2 = explore_path(path)
    files1 = get_sheet_data("Files")

    # Remove same file 
    for g in files1:
        compare_temp = {"filename": g["filename"],"path": g["path"],"size": g["size"]}
        if compare_temp in files2:
            files1.remove(g)
            files2.remove(compare_temp)

    files2 = hash_files(files2)
    # Combine 2 files
    combine_list = [{**f, **{"new":0}} for f in files1] + [{**f, **{"new":1}} for f in files2]
    hash_combine_list = [f["hash"] for f in combine_list]
    same_hash = list( set(f for f in hash_combine_list if hash_combine_list.count(f)>1 ))
    diff_hash = list(set(hash_combine_list) - set(same_hash))
    del_list = []
    add_list = []
    change_list = []

    # Xử lý với same_hash
    for hashstr in same_hash:
        temp1 = [f for f in files1 if f["hash"]==hashstr ]
        temp2 = [f for f in files2 if f["hash"]==hashstr ]
        # Nếu sửa tên/path
        if len(temp1)==1 and len(temp2)==1:
            change_list+=[ [temp1,temp2] ]
        # Nếu thêm/xóa 2 file duplicate ở 2 path khác nhau
        elif len(temp1) >1 and len(temp2)==0:
            del_list+=temp1
        elif len(temp1)==0 and len(temp2)>1:
            add_list+=temp2
        # Nếu đổi tên + duplicate ( trường hợp khá là hiếm)
        elif len(temp1)>0 and len(temp2)>0:
            pass

    # Xử lý với diff_hash:
    for hashstr in diff_hash:
        temp1 = [f for f in files1 if f["hash"] == hashstr ]
        if len(temp1)==0:
            temp2 = [f for f in files2 if f["hash"] == hashstr ]
            add_list+=temp2
        else:
            del_list+=temp1

    # ADD files to entry sort by path
    paths = list(set([f["path"] for f in add_list]))
    paths = sorted(paths, key=lambda f: 0-f.count("\\") )

    count = 0
    for pat in paths:
        logging.info("ADD {} to change sheet... Progress: {}/{} - {}%".format(pat, str(count), str(len(paths)), str(count/len(paths)*100) ))
        count+=1
        temp = [f for f in add_list if f["path"] == pat ]
        temp = sorted(temp, key=lambda f: f["filename"] )

        # Thêm thông tin + predic vào temp(list các dict có cùng path)
        for i in range(len(temp)):
            temp[i].update(add_file( temp[i]["filename"] , temp[i]["path"] ) )

        # Ktra xem tất cả trong temp có cùng 1 predic ko ?
        predic_all = [f["mal_id"] for f in temp]

        # Nếu đúng: In warning với các bộ không cùng số đông
        while len(set(predic_all))>1:
            logging.warning(f"Folder {pat} add file not same result in all files")
            predic_all = sorted(predic_all, key=lambda f: predic_all.count(f))

            [f for f in temp if f["mal_id"]==predic_all[0]][0].update({"warning":1})
            predic_all.remove(predic_all[0])

    add_list = sorted(add_list, key=lambda f: f["path"] )
    # Chuyển tất cả vào sheet change
    create_change_sheet(add_list,del_list,change_list)

print(commit_folder("D:\\Anime"))

# push()
