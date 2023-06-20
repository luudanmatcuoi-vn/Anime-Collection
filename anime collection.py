import configparser
from imohash import hashfile
from os import listdir, system
from os.path import isfile, isdir, join, getsize
import ffmpeg, json, xmltodict, sqlite3, requests
import anitopy, textdistance, sys
from mal import AnimeSearch, Anime
from tabulate import tabulate

config = configparser.ConfigParser()

# ##################################
# # Hàm khám phá tất cả media trong folder rootpath
# files = [] 
# def explore(path):
#     #Add files from this folder
#     fi =[]
#     try:
#         for f in listdir(path):
#             if isfile(join(path,f)) and ("mkv" in f[-4:].lower() or "mp4" in f[-4:].lower() ):
#                 fi+=[f]
#     except:
#         print(f"Folder {path} can't explore. Please check again")
#     global files
#     for f in fi:
#         hashf = hashfile(join(path,f), hexdigest=True)
#         files = files + [ {'filename':f , 'path':path , 'hash':hashf} ]
#     #Scan subfolders
#     try:
#         fo = [f for f in listdir(path) if not isfile(join(path,f)) ]
#     except:
#         print("errorfolder")
#         fo=[]

#     fo.sort()
#     for folder in fo:
#         sys.stdout.write("\rQuét folder: "+join(path,folder)+" "*(150-len(path)))
#         sys.stdout.flush()
#         explore(join(path,folder))
#     return ''

# # Hàm lấy metadata của 1 file==> Trả kết quả
# def metadata(filepath):
#     vid = ffmpeg.probe(filepath)
#     metavid = [f for f in vid['streams'] if f['codec_type'] == 'video'][0]
#     result={}
#     result["width"] = metavid["width"]
#     result["height"] = metavid["height"]
#     result["filesize"] = getsize(filepath)
#     result["duration"]=vid["format"]["duration"]
#     result["bitrate"]=vid["format"]["bit_rate"]
#     result["softsub"] = bool([f for f in vid['streams'] if f['codec_type'] == 'subtitle'])
#     return result
    
# # Hàm select
# def select(cur, table ,condition="1==1"):
#     a = "Select * FROM " + table + " WHERE " + condition
#     cur.execute( a )
#     columns = [col[0] for col in cur.description]
#     rows = [dict(zip(columns, row)) for row in cur.fetchall()]
#     return rows
# ###############################################



# for t in files:
#     if t["softsub"]=='False': sub='hardsub'
#     else: sub = 'softsub'
#     if "release_group" not in t:
#         t["release_group"] = ''
#     print( t["filename"]+ '\t' + t["duration"]+ '\t' + sub + '\t' + str(t["width"])+ '\t' + str(t["height"]) + '\t' + str(t["filesize"])+ '\t' +  t["release_group"] )

# def maltoken():
#     system("python mal-gettoken.py")
#     file =open("token.json","r")
#     token = json.load(file)
#     global access_token
#     access_token = token["access_token"]



#############################################################
################PHẦN ĐIỀU KHIỂN CHƯƠNG TRÌNH ################
maltoken()
while True:
    #### Print menu
    print("           ANIME COLLECTION")
    print("1. Scan your collection")
    print("2. Find AnimeID using trace.moe api")
    print("3. Find AnimeID in myanimelist and tag it")
    print("4. Check files health")
    print("5. Input tag to MAL")
    print("")
    inp = input("Type your answer: ")

    if inp == '1':
        system('cls')
        print("Scan your collection")
        print("The default root is "+rootpath+ " drag n drop new root to change root or leave blank")
        inp = input("Type your answer: ")
        if inp != "": rootpath=str(inp)
        explore(rootpath)
        filesdata = select(cur, "Files")
        filesdata = [{'filename':t['Filename'] , 'path':t['Path'] , 'hash':t['Hash'] } for t in filesdata]
        # Check sự thay đổi các biến
        compare = []
        tempfilesdata = [t['hash'] for t in filesdata]
        for t in files:
            if t["hash"] not in tempfilesdata:
                t["compare"] = "add"
                compare+= [t]
            else:
                g = [w for w in filesdata if w["hash"]==t["hash"] ][0]
                if not t['filename'] == g['filename']:
                    t["compare"] = "changename"
                elif not t['path'] == g['path']:
                    t["compare"] = "changepath"
                else:
                    t["compare"] = "same"
                compare += [t]

        addf = [g for g in compare if g["compare"]=="add"]
        changenamef = [g for g in compare if g["compare"]=="changename"]
        changepathf = [g for g in compare if g["compare"]=="changepath"]
        removef = [ g for g in filesdata if g["hash"] not in [w["hash"] for w in files]]
        print("")
        print("Need change: ")
        print("Add "+str(len(addf))+" entry")
        print("Change name "+str(len(changenamef))+" entry")
        for g in changenamef:
            print(g["filename"])
        print("Change path "+str(len(changepathf))+" entry")
        for g in changepathf:
            print(g["filename"]+"\t"+g["path"])
        inp=input("Do you want continue ? (1/0)")
        if inp != "1": continue

        #### ADD new files to database
        for fi in range(len(addf)):
            sys.stdout.write("\rGet info file: "+ addf[fi]["filename"] +" "*(150-len(addf[fi]["filename"]))+str(fi+1)+"/"+str(len(addf)))
            sys.stdout.flush()

            addf[fi] = {**addf[fi], **metadata(join(addf[fi]["path"],addf[fi]["filename"]))}
            info = anitopy.parse(files[fi]["filename"])
            addf[fi]["hash"] = hashfile(join(addf[fi]["path"],addf[fi]["filename"]), hexdigest=True)
            try:
                addf[fi]["anime_title"] = info["anime_title"]
            except:
                pass
            try:
                addf[fi]["release_group"] = info["release_group"]
            except:
                pass   
            try:
                addf[fi]["episode_number"] = info["episode_number"]
            except:
                pass

        for f in addf:
            if "release_group" not in f: f["release_group"]=''
            f["filename"] = f["filename"].replace("'","''")
            f["path"] = f["path"].replace("'","''")
            f["release_group"] = f["release_group"].replace("'","''")
            a= "INSERT or replace INTO Files (Filename,Hash,Path,Filesize,Width,Height,Duration,Bitrate,Fansub,Softsub,Status) Values ('{}','{}','{}',{},{},{},{},{},'{}',{},{}) \
            ".format(f["filename"],f["hash"],f["path"],f["filesize"],f["width"],f["height"],f["duration"],f["bitrate"],f["release_group"],f["softsub"],"'Local'")
            cur.execute( a )
        connect.commit()

        ### Change info of files in database
        for f in changenamef:
            f["filename"] = f["filename"].replace("'","''")
            cur.execute("UPDATE Files SET Filename = '"+f["filename"]+"' where Hash=='"+f["hash"]+"'")
        
        for f in changepathf:
            f["path"] = f["path"].replace("'","''")
            cur.execute("UPDATE Files SET Path = '"+f["path"]+"' where Hash == '"+f["hash"]+"'")
        connect.commit()

        if len(removef)>0:
            print("You remove "+str(len(removef))+" files in local, do you want remove from database ?")
            inp = input("Type your answer")
            if inp =="1":
                for f in removef:
                    cur.execute("DELETE FROM Files WHERE Hash == '"+f["hash"]+"'")
                connect.commit()
        print("Done!!!")
        files = []
        input()
        continue

    ############### Find AnimeID using MAL animesearch  
    if inp == "3":
        while True:
            system('cls')
            print("Searching ....")
            files=select(cur, "Files", "AnimeID is NULL")
            if len(files)==0:
                print(" Nothing left :) ")
                input()
                continue
            files[0]['Path'] = files[0]['Path'].replace("'","''")
            files = select(cur, "Files", "AnimeID is NULL AND Path == '"+files[0]['Path']+"'")
            files = sorted(files, key=lambda d: d['Filename']) 
            for i in range(len(files)):
                info = anitopy.parse(files[i]["Filename"])
                try:
                    files[i]["anime_title"] = info["anime_title"]
                except:
                    files[i]["anime_title"] = 'error'
            files = [f for f in files if f["anime_title"]!='']
            files = [f for f in files if f["anime_title"] == files[0]["anime_title"]]
            print(files[0]["Path"])

            # Search anime using anime_title
            try:
                search = AnimeSearch(files[0]["anime_title"])
                temp = []
                for i in range(len(files)):
                    temp +=[ [files[i]["Filename"] , str(i+1)+". "+str(search.results[i].mal_id)+" "+str(search.results[i].title)]]
            except:
                inp = input("Your MAL search keyword: ")
                search = AnimeSearch(inp)
                temp = []
                for i in range(len(files)):
                    temp +=[ [files[i]["Filename"] , str(i+1)+". "+str(search.results[i].mal_id)+" "+str(search.results[i].title)]]

            temp = []
            for i in range(len(files)):
                temp +=[ [str(i+1)+". "+files[i]["Filename"] , str(i+1)+". "+str(search.results[i].mal_id)+" "+str(search.results[i].title)]]

            print(tabulate(temp, headers = ["filename","MAL"]))
            print("0. Skip")
            print("String to search new keyword")
            inp = input("Type your answer: ")

            if inp == "0":
                for f in files:
                    cur.execute("UPDATE Files SET AnimeID = "+str(0)+" where Hash == '"+f["Hash"]+"'")
            
            elif inp =='extra':
                for f in files:
                    cur.execute("UPDATE Files SET Tags = 'extra' where Hash == '"+f["Hash"]+"'")
            elif inp =='extra0':
                for f in files:
                    cur.execute("UPDATE Files SET Tags = 'extra' where Hash == '"+f["Hash"]+"'")    
                    cur.execute("UPDATE Files SET AnimeID = 0 where Hash == '"+f["Hash"]+"'")

            elif inp =='amv':
                for f in files:
                    cur.execute("UPDATE Files SET Tags = 'amv' where Hash == '"+f["Hash"]+"'")
                    cur.execute("UPDATE Files SET AnimeID = 0 where Hash == '"+f["Hash"]+"'")

            elif inp =='mv':
                for f in files:
                    cur.execute("UPDATE Files SET Tags = 'mv' where Hash == '"+f["Hash"]+"'")
            elif inp =='mv0':
                for f in files:
                    cur.execute("UPDATE Files SET Tags = 'mv' where Hash == '"+f["Hash"]+"'")
                    cur.execute("UPDATE Files SET AnimeID = 0 where Hash == '"+f["Hash"]+"'")

            elif bool(inp.isdigit()) :
                for f in files:
                    cur.execute("UPDATE Files SET AnimeID = "+str(search.results[int(inp)-1].mal_id)+" where Hash == '"+f["Hash"]+"'")
            
            elif set(inp) <= set("0123456789 -"):
                inp = inp.split(' ')
                if bool(inp[0].isdigit()):
                    cur.execute("UPDATE Files SET AnimeID = "+str(search.results[int(inp[1])-1].mal_id)+" where Hash == '"+files[int(inp[0])-1]["Hash"]+"'")
                else:
                    for f in files[int(inp[0].split('-')[0])-1:int(inp[0].split('-')[1])]:
                        cur.execute("UPDATE Files SET AnimeID = "+str(search.results[int(inp[1])-1].mal_id)+" where Hash == '"+f["Hash"]+"'")

            else:
                search = AnimeSearch(inp)
                try:
                    for t in range(5):
                        print(str(t+1)+'. '+str(search.results[t].mal_id)+" "+str(search.results[t].title))
                except:
                    pass
                inp = input("Type your answer: ")
                for f in files:
                    cur.execute("UPDATE Files SET AnimeID = "+str(search.results[int(inp)-1].mal_id)+" where Hash == '"+f["Hash"]+"'")
            connect.commit()

    if inp=="2":
        maltoken()
        
    if inp=="5":
        files = select(cur,"Files","AnimeID is not NULL")
        local_tags_list = [f["AnimeID"] for f in files]
        local_tags_list = list(set(local_tags_list))
        local_tags_list.remove(0)
        print(local_tags_list)

        for animeid in local_tags_list:
            url = f"https://api.myanimelist.net/v2/anime/{animeid}/my_list_status"
            response = requests.patch(url, headers = {
                'Authorization': f'Bearer {access_token}',
                "Content-Type": "application/x-www-form-urlencoded"
                }, data = { "tags":"local" } )
            response.raise_for_status()
            print(response.json())
            response.close()
        



























# import malclient
# client = malclient.Client()
# client.init(access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6IjMwMzI2ZTljZmQ0MzlhNTU0NzUzZDc3MmQwZDY2YThjZjAxNzY2OWM0ZThkMjM3ZjUxMjdiZWI3OTlmYTFiNmUwMTFkNTA3YjM2MTA0MzJhIn0.eyJhdWQiOiI2ODJkNTlhZDIyOWViOTBlM2VhZjJhZWZlNjJjYjFmNyIsImp0aSI6IjMwMzI2ZTljZmQ0MzlhNTU0NzUzZDc3MmQwZDY2YThjZjAxNzY2OWM0ZThkMjM3ZjUxMjdiZWI3OTlmYTFiNmUwMTFkNTA3YjM2MTA0MzJhIiwiaWF0IjoxNjQ4NzQwNjA5LCJuYmYiOjE2NDg3NDA2MDksImV4cCI6MTY1MTQxOTAwOSwic3ViIjoiNjAyODM3MyIsInNjb3BlcyI6W119.B-p1X0XNPh9ljuNwT_R2YkFXuMAFbGWg0GdVtJyM4xBzYKMqemldw6PGJbA90f_E_7mBV7Mp7tHo1stv6rGFwm1LHbb60EexRf_4tw_xYF8pUL8XBcT16aQDq9lir0vMPJi-Yqzb29NxuBo0xw9BOHAjBWA1mlFxaaUX3mjXD37sfQ7sio6dZjKEAjc4H2KX8Xg34eYClQztw8bzQUUck7eFBabI5P8pXqeGLTHvElvhquzMqjxpr0aOG8g-DdL1MCktVoQrviutena1-hHj7P_llZ7CbeCqklt3WUf_-5RhsKMAogKP0doDgoAf8wE8sAboZUgRODO3JxnY1d3RYQ")
# # # get my user info
# # print(client.get_user_info())
# # get my anime list (you can get other users by name)
# animes = client.get_user_anime_list('luudanmatcuoi')
# for anime in animes:
#     print(anime.title, anime.id, anime.score, anime.status)



# # search anime, returns list
# anime = client.search_anime("cowboy", limit=20)
# for ani in anime:
#     # print all attributes as dictionary for refference
#     print(ani)
#     # print attribute
#     print(ani.title)





# #Commit nạp myanimelist.xml --> database
# with open("animelist_1649250580_-_6028373.xml") as xml_file:
#     animecollection = xmltodict.parse(xml_file.read())
# for t in animecollection["myanimelist"]["anime"]:
#     t["series_title"] = t["series_title"].replace("'","''")
#     t["my_tags"] = str(t["my_tags"]).replace("None","")
#     a = "INSERT or replace INTO Anime (ID,Title,Type,Episodes,Score,my_status,my_tags) VALUES ({},'{}','{}',{},{},'{}','{}') \
#         ".format(t["series_animedb_id"],t["series_title"],t["series_type"],t["series_episodes"],t["my_score"],t["my_status"],t["my_tags"])
#     print(a)
#     cur.execute( a )
# connect.commit()
# connect.close()

# animecollection = [t for t in animecollection["myanimelist"]["anime"]]






# # Commit nạp file -> database files ( không bao gồm AnimeID, Source, Fansub phải sửa lại)
# ani = select(cur, "Anime")
# anitable = []
# i = 0
# for t in ani:
#     for b in range(int(t["Episodes"])):
#         anitable.append( {"index":i, "animeid":t["ID"], "ep":b+1, "text": str(t["Title"])+" "+str(b+1) } )
#         i+=1
# for f in files:
#     a= "INSERT or replace INTO Files (Filename,Hash,Path,Filesize,Width,Height,Duration,Bitrate,Fansub,Softsub,Status) Values ('{}','{}','{}',{},{},{},{},{},'{}',{},{}) \
#     ".format(f["filename"],f["hash"],f["path"],f["filesize"],f["width"],f["height"],f["duration"],f["bitrate"],f["release_group"],f["softsub"],"'Local'")
#     print(a)
#     cur.execute( a )
# connect.commit()
# connect.close()




# b = select(cur, "Files","softsub==NULL")
# cur.execute("UPDATE Files SET Fansub = 'KNFa' where Softsub==NULL")
# connect.commit()
