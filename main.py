import os
import configparser
import argparse
import shutil
import time
import json
import requests
import colorama

from youtube_uploader_selenium import YouTubeUploader
from urllib.parse import urlparse


#---> GLOBAL VARIABLES

#Create a ConfigParser object
config = configparser.ConfigParser()

#Read the config.ini file
config.read('config.ini')

#Get the values from the config.ini file
PROFILE_PATH = config.get('DEFAULT', 'PROFILE_PATH')
VIDEOS_FOLDER_PATH = config.get('DEFAULT', 'VIDEOS_FOLDER_PATH')
PERIOD_STR = config.get('DEFAULT', 'PERIOD_STR')
LOWERCASE_WORDS = [word.strip() for word in config.get('WORDS', 'LOWERCASE').split(',')]
UPPERCASE_WORDS = [word.strip() for word in config.get('WORDS', 'UPPERCASE').split(',')]

#Initialize colorama
colorama.init()


#---> FUNCTIONS

#List all folders in the directory
def list_folders(folder_path):
    """Devuelve una lista de todas las carpetas en el directorio dado."""
    elements = os.listdir(folder_path)
    folders = [elem for elem in elements if os.path.isdir(os.path.join(folder_path, elem))]
    return folders

#Delete all files and folders in the directory
def delete_all_files_and_folders(folder_path):
    """Elimina todos los archivos y carpetas en el directorio dado."""
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(colorama.Fore.RED + f'ERROR al eliminar {file_path}. Razón: {e}')

#Read a json file
def read_json_file(file_path):
    """Lee un archivo JSON y devuelve los datos."""
    with open(file_path, 'r', encoding="utf8") as file:
        json_obj = json.load(file)
    return json_obj

#Write a json file
def write_json(file_path, data):
    """Escribe los datos en un archivo JSON."""
    with open(file_path, 'w', encoding="utf-8") as file:
        json.dump(data, file)
    return file_path

#Get the file name from the last part of the url
def get_file_name_from_url(url):
    """Obtiene el nombre del archivo de la última parte de la URL dada."""
    return os.path.basename(urlparse(url).path)

#Download a file from a url and save it in videos folder
def download_file(url, file_name):
    """Descarga un archivo de una URL y lo guarda en la carpeta de videos. Si hay un error al descargar, devuelve False. Si se descarga correctamente, devuelve True."""
    file_path = os.path.join(VIDEOS_FOLDER_PATH, os.path.splitext(file_name)[0], file_name)
    file_dir = os.path.dirname(file_path)

    try:
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)

        r = requests.get(url)
        with open(file_path, 'wb') as file:
            file.write(r.content)

        return True

    except Exception as e:
        print(colorama.Fore.RED + f'ERROR al descargar {file_name}. Razón: {e}')
        return False

#Format a string as title, keeping some words in lowercase and others in uppercase
def format_string_as_title(str):
    """Formatea una cadena de texto como título, manteniendo algunas palabras en minúsculas y otras en mayúsculas."""
    words = str.title().split()
    formatted_words = [word.upper() if word.upper() in UPPERCASE_WORDS else 
                       word.lower() if i != 0 and word.lower() in LOWERCASE_WORDS else 
                       word for i, word in enumerate(words)]
    return " ".join(formatted_words)

#Calculate the elapsed time
def calculate_elapsed_time(start, end):
    """Calcula el tiempo transcurrido entre dos marcas de tiempo."""
    elapsed_time = end - start
    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)
    seconds = int(elapsed_time % 60)
    return hours, minutes, seconds


#---> MAIN PROCESS STARTS HERE

#Create the argument parser
parser = argparse.ArgumentParser()

#Add the arguments to the parser
parser.add_argument("--json", help="Ruta al archivo JSON")
parser.add_argument("--download", help="Indica si solo se debe ejecutar el proceso de descarga de videos", action="store_true")
parser.add_argument("--upload", help="Indica si solo se debe ejecutar el proceso de subida de videos", action="store_true")
parser.add_argument("--noheadless", help="Indica que Firefox no se debe ejecutar en modo headless", action="store_false")

#Parse the arguments
args = parser.parse_args()

#Get the json file path from the arguments
json_file_path = args.json

#Get the download flag from the arguments (False by default)
download = args.download

#Get the upload flag from the arguments (False by default)
upload = args.upload

#Get the headless mode flag from the arguments (True by default)
headless_mode = args.noheadless

#Check if the json file path or the upload flag was provided
if not json_file_path and not upload:
    print(colorama.Fore.CYAN + 'Debe proporcionar la ruta al archivo JSON o usar el argumento --upload.')
    print('Ejemplo: python main.py --json "C:\\Users\\user\\Desktop\\videos.json"')
    exit()

#Check if PROFILE_PATH exists
if not os.path.exists(PROFILE_PATH):
    print(colorama.Fore.YELLOW + 'El perfil de Firefox no existe. Verifique el archivo config.ini.')
    exit()


#If the upload flag was not provided, execute the DOWNLOAD process first
if not upload:

    #Check if the json file exists
    if not os.path.exists(json_file_path):
        print(colorama.Fore.YELLOW + 'El archivo JSON no existe. Verifique la ruta proporcionada.')
        exit()
    
    #Read the json file
    json_data = read_json_file(json_file_path)
    
    #Check if the videos folder exists, if not, create it
    if not os.path.exists(VIDEOS_FOLDER_PATH):
        #Create the videos folder
        print(colorama.Fore.YELLOW + 'AVISO: La carpeta de videos no existe. Se creará la carpeta vacía.')
        os.makedirs(VIDEOS_FOLDER_PATH)     

    #Start the timer to measure the elapsed time of the whole process
    time_start = time.time()

    #List to store the videos that were not downloaded due to an error
    not_downloaded_videos = []

    print(colorama.Fore.MAGENTA + '************************************************')
    print(colorama.Fore.WHITE + '---> Descargando videos...')

    #Iterate over the JSON data to download the videos
    for index, rec in enumerate(json_data):
        date = rec['date']
        subjectId = rec['subjectId']
        subjectName = rec['subjectName']
        teacher = rec['teacher']

        print(colorama.Fore.MAGENTA + '************************************************')
        print(colorama.Fore.GREEN + 'Video ' + str(index + 1) + ' de ' + str(len(json_data)) + ': ' + date + ' - ' + subjectId)

        videos = rec['videos']

        #Iterate over the videos in the class
        for video in videos:
            downloadUrl = video['downloadUrl']

            #Get the file name from the video url
            file_name = get_file_name_from_url(downloadUrl)

            #Check if the video is already downloaded in the videos folder
            if os.path.exists(os.path.join(VIDEOS_FOLDER_PATH, os.path.splitext(file_name)[0], file_name)):
                print(colorama.Fore.YELLOW + 'AVISO: Omitiendo video ya descargado. ' + file_name)
                continue

            #Download the video
            if download_file(downloadUrl, file_name):
                print(colorama.Fore.GREEN + 'Descargado: ' + file_name)
            else:
                #Add the current video to the Not downloaded videos list
                not_downloaded_videos.append(downloadUrl)
            
            #Format the subject name as title
            formatted_title = format_string_as_title(subjectName)
            
            #Create the metadata content
            metadata_content = {"title": formatted_title + " " + PERIOD_STR + " S00", 
                                "description": subjectName + "\n" + subjectId + "\n" + teacher + "\n" + date}
            
            #Get the metadata path
            metadata_path = os.path.join(VIDEOS_FOLDER_PATH, os.path.splitext(file_name)[0], 'metadata.json')
            
            #Write the metadata content to a json file
            write_json(metadata_path, metadata_content)


    #Check if there are videos that were not downloaded due to an error and try to download them again
    if len(not_downloaded_videos) > 0:
        
        failed_download_retries = []

        print(colorama.Fore.MAGENTA + '************************************************')
        print(colorama.Fore.YELLOW + '---> Reintentando descarga de videos...')

        #Iterate over the Not downloaded videos list
        for index, downloadUrl in enumerate(not_downloaded_videos):

            print(colorama.Fore.MAGENTA + '************************************************')
            print(colorama.Fore.GREEN + 'Video ' + str(index + 1) + ' de ' + str(len(not_downloaded_videos)))
            
            #Get the file name from the download url
            file_name = get_file_name_from_url(downloadUrl)

            #Try to download the video
            if download_file(downloadUrl, file_name):
                print(colorama.Fore.GREEN + 'Descargado: ' + file_name)
            else:
                print(colorama.Fore.RED + 'ERROR reintentando descargar: ' + file_name)

                #Add the current video and the following videos to the failed download retries list  
                failed_download_retries.append(downloadUrl)
                failed_download_retries.extend(not_downloaded_videos[index + 1:])

                #Delete each video folder in the failed download retries list
                for downloadUrl in failed_download_retries:
                    file_name = get_file_name_from_url(downloadUrl)
                    folder_path = os.path.join(VIDEOS_FOLDER_PATH, os.path.splitext(file_name)[0])
                    delete_all_files_and_folders(folder_path)
                    os.rmdir(folder_path)

                #Calculate the elapsed time and exit the script
                print(colorama.Fore.MAGENTA + '************************************************')
                print(colorama.Fore.WHITE + '---> Proceso finalizado')
                time_end = time.time()
                hours, minutes, seconds = calculate_elapsed_time(time_start, time_end)
                print(colorama.Fore.CYAN + f'Tiempo total transcurrido: {hours} horas, {minutes} minutos y {seconds} segundos')
                print(colorama.Fore.MAGENTA + '************************************************')
                exit()
            
else:
    #Check if the videos folder exists
    if not os.path.exists(VIDEOS_FOLDER_PATH):
        #Create the videos folder
        os.makedirs(VIDEOS_FOLDER_PATH)
        print(colorama.Fore.YELLOW + 'AVISO: La carpeta de videos no existe. Se creará la carpeta vacía.')
        print('Compruebe que esta contenga los videos a subir antes de ejecutar el script nuevamente.')
        exit()

    #Start the timer to measure the elapsed time of the UPLOAD process
    time_start = time.time()


#Check if the download flag was provided to stop the script here
if download:
    print(colorama.Fore.MAGENTA + '************************************************')
    print(colorama.Fore.WHITE + '---> Proceso de descarga finalizado')

    #Stop the timer
    time_end = time.time()

    #Calculate the elapsed time
    hours, minutes, seconds = calculate_elapsed_time(time_start, time_end)
    
    #Print the elapsed time
    print(colorama.Fore.CYAN + f'Tiempo total transcurrido: {hours} horas, {minutes} minutos y {seconds} segundos')
    print(colorama.Fore.MAGENTA + '************************************************')
    exit()


#Download process finishes and the UPLOAD process starts here

#List all folders in the videos folder
video_folders = list_folders(VIDEOS_FOLDER_PATH)

#Check if there are no video folders in the videos folder
if len(video_folders) == 0:
    print(colorama.Fore.YELLOW + 'AVISO: No hay videos para subir en la carpeta de videos.')
    exit()

#Sort the video folders by name in ascending order
video_folders.sort()

#List to store the uploaded videos 
uploaded_videos = []

#List to store the pending videos to upload in case of an error
pending_videos = []

#Check if the cookies file not exists to desactivate the headless mode
if not os.path.exists('youtube.com.pkl'):
    headless_mode = False

print(colorama.Fore.MAGENTA + '************************************************')
print(colorama.Fore.WHITE + '---> Subiendo videos a Youtube...')

#Iterate over the video folders
for index, folder in enumerate(video_folders):
    try:
        video_path = os.path.join(VIDEOS_FOLDER_PATH, folder, folder + '.mp4')
        metadata_path = os.path.join(VIDEOS_FOLDER_PATH, folder, 'metadata.json')

        print(colorama.Fore.MAGENTA + '************************************************')
        print(colorama.Fore.GREEN + 'Video ' + str(index + 1) + ' de ' + str(len(video_folders)) + ': ' + folder)

        uploader = YouTubeUploader(video_path, metadata_path, None, PROFILE_PATH, headless_mode)
        was_video_uploaded, video_id = uploader.upload()
        if was_video_uploaded:
            uploaded_videos.append(folder) 
        assert was_video_uploaded

    except Exception as e:
        #Add the current folder to the pending videos list
        pending_videos.append(folder)

        #Get the exception message
        exception_message = str(e).strip()

        #Compare exception message to check if the upload limit was reached
        if exception_message == 'Message: Element <ytcp-button id="next-button" class="style-scope ytcp-uploads-dialog" type="filled"> could not be scrolled into view':
            print(colorama.Fore.RED + 'ERROR: Se alcanzó el límite de subida de videos.')
            #Add the following videos to the pending videos list
            pending_videos.extend(video_folders[index + 1:])
            #Stop the loop
            break

        #If the exception message is different
        else:
            print(colorama.Fore.RED + 'ERROR al subir el video. ' + exception_message)


#Delete uploaded videos from the videos folder
for video in uploaded_videos:
    #Delete the video file and the metadata file in the video folder
    delete_all_files_and_folders(os.path.join(VIDEOS_FOLDER_PATH, video))
    #Delete the video folder
    os.rmdir(os.path.join(VIDEOS_FOLDER_PATH, video))

#Print the pending videos if there are any
if len(pending_videos) > 0:
    print(colorama.Fore.MAGENTA + '************************************************')
    print(colorama.Fore.WHITE + '---> ' + str(len(pending_videos)) + ' Videos pendientes para subir:')
    print(colorama.Fore.YELLOW + str(pending_videos))

print(colorama.Fore.MAGENTA + '************************************************')
print(colorama.Fore.WHITE + '---> Proceso finalizado')

#Stop the timer
time_end = time.time()

#Calculate the elapsed time
hours, minutes, seconds = calculate_elapsed_time(time_start, time_end)

#Print the elapsed time
print(colorama.Fore.CYAN + f'Tiempo total transcurrido: {hours} horas, {minutes} minutos y {seconds} segundos')
print(colorama.Fore.MAGENTA + '************************************************')
exit()
