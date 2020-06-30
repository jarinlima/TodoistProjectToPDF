import pandas as pd 
import todoist
import json
from datetime import datetime
import pytz
import numpy as np
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from matplotlib import pyplot as plt
import parsedatetime
import argparse
import sys
import yaml

def parsecliarguments():
    # Parseamos los argumentos de la linea de comandos
    parser = argparse.ArgumentParser()
    parser.add_argument('--configfile', help='Ruta hacia el archivo de configuración. Ex. --fromdate="config.yaml"', required=True)
    args = parser.parse_args()
    
    # Leo el archivo de configuración y parseamos el .yml hacia un dict
    f = open(args.configfile)
    data = yaml.load(f, Loader=yaml.FullLoader)

    fromdate = data["fromdate"]
    todate = data["todate"]
    timezone = data["timezone"]
    idproject = data["idproject"]
    apikey = data["apikey"]
    baseurl = data["baseurl"]
    stylesheets = data["stylesheets"]

    # Parseando fromdate y todate
    cal = parsedatetime.Calendar()
    time_struct, parse_status = cal.parse(fromdate)
    if parse_status == 0:
        print("Parámetro 'fromdate' inválido, Ayuda -h")
        sys.exit()
    fromdate = datetime(*time_struct[:6]).strftime('%Y-%m-%dT%H:%M:%SZ')
    fromdatefortemplate = datetime(*time_struct[:6]).strftime('%Y-%m-%d %H:%M:%S')

    time_struct, parse_status = cal.parse(todate)
    if parse_status == 0:
        print("Parámetro 'todate' inválido, Ayuda -h")
        sys.exit()
    todate = datetime(*time_struct[:6]).strftime('%Y-%m-%dT%H:%M:%SZ')
    todatefortemplate = datetime(*time_struct[:6]).strftime('%Y-%m-%d %H:%M:%S')
    ## Convirtiendo hora local, en hora UTC
    ### todate
    local = pytz.timezone(timezone)
    naive = datetime.strptime (todate, "%Y-%m-%dT%H:%M:%SZ")
    local_dt = local.localize(naive, is_dst=None)
    utc_dt = local_dt.astimezone(pytz.utc)
    todate = utc_dt.strftime ("%Y-%m-%dT%H:%M:%SZ")
    ### fromdate
    naive = datetime.strptime (fromdate, "%Y-%m-%dT%H:%M:%SZ")
    local_dt = local.localize(naive, is_dst=None)
    utc_dt = local_dt.astimezone(pytz.utc)
    fromdate = utc_dt.strftime ("%Y-%m-%dT%H:%M:%SZ")
    return fromdate, todate, fromdatefortemplate, todatefortemplate, timezone, idproject, apikey, baseurl, stylesheets

# Extraemos las tareas completadas
def getCompletedTasks(fromdate,todate,idproject,api):
    ## offset y limite ya que el api no devuelve todo de una vez, sino que por paginas
    offset = 0
    limit = 100

    completedtasks = []

    i = 1
    while True:
        data = api.completed.get_all(since=fromdate, until=todate,limit=limit, offset=offset,project_id=idproject)
        if not data["items"]:
            break
        completedtasks.extend(data["items"])
        offset += limit
    return completedtasks
def getCompletedTasksDataFrame(completedtasks, timezone):
    # Creamos el dataframe para manipular las completedtasks
    df_completedtasks = pd.DataFrame(completedtasks)
    df_completedtasks = df_completedtasks[["id","content","completed_date"]]
    
    # Renombrando las columnas del dataframe
    df_completedtasks.rename(columns={'content':'Tarea','completed_date':'Completada','id':'Id'}, inplace=True)
    ## Convierto la columnda de la fecha en que se completo de string al tipo datetime
    ## Y la cambio por la zona horaria pasado por el argumento timezone
    df_completedtasks['Completada'] = pd.to_datetime(df_completedtasks.Completada, format='%Y-%m-%dT%H:%M:%SZ')
    df_completedtasks['Completada'] = df_completedtasks['Completada'].dt.tz_localize('utc').dt.tz_convert(timezone)
    df_completedtasks['Completada'] = pd.to_datetime(df_completedtasks["Completada"].dt.strftime('%Y-%m-%d %H:%M:%S'))
    return df_completedtasks

def getUncompletedTasks(idproject, api):
    # Extraemos las tareas incompletas
    todotasks = api.projects.get_data(idproject)
    return todotasks["items"]

def getUncompletedTasksDataframe(uncompletedtasks, timezone):
    df_uncompletedtasks = pd.DataFrame(uncompletedtasks)
    df_uncompletedtasks = df_uncompletedtasks[["id","content","date_added"]]
    # Renombrando las columnas del dataframe
    df_uncompletedtasks.rename(columns={'content':'Tarea','date_added':'Creación','id':'Id'}, inplace=True)
    ## Convierto la columna de la fecha en que se creó la tarea de string al tipo datetime
    ## Y la cambio por la zona horaria pasado por el argumento timezone
    df_uncompletedtasks['Creación'] = pd.to_datetime(df_uncompletedtasks["Creación"], format='%Y-%m-%dT%H:%M:%SZ')
    df_uncompletedtasks['Creación'] = df_uncompletedtasks['Creación'].dt.tz_localize('utc').dt.tz_convert(timezone)
    df_uncompletedtasks['Creación'] = pd.to_datetime(df_uncompletedtasks["Creación"].dt.strftime('%Y-%m-%d %H:%M:%S'))
    return df_uncompletedtasks

def generatePNGPieChart(filename,lendf_completedtasks, lendf_uncompletedtasks):
    labels = 'Tareas Completadas', 'Tareas Pendientes'
    sizes = [lendf_completedtasks, lendf_uncompletedtasks]
    explode = (0,0.2)
    fig1, ax1 = plt.subplots()
    ax1.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%',
            shadow=True, startangle=90,textprops={'family': "sans-serif","fontsize":15})
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.savefig(filename,bbox_inches='tight')

def generatePNGBarhChart(filename,df_completedtasks):
    ## Grafica barh

    plt.figure(figsize=(23, 12))

    ### Le agrego una columna más para quitor la hora y dejar solo la fecha para luego poder agrupar por dia
    df_completedtasks['CompletadaFecha'] = df_completedtasks['Completada'].dt.date
    ### Genero una gráfica de barras horizontal, con la cantidad de tareas por dia
    ax = (df_completedtasks["CompletadaFecha"].groupby(df_completedtasks['CompletadaFecha']).count()).plot(kind="barh",color=plt.cm.inferno_r(np.linspace(.4,.8, 7)))
    ax.set_facecolor('#eeeeee')
    ax.set_xlabel("# Tareas Completadas por dia",fontsize=25, family="sans-serif")
    ax.set_ylabel("Fecha", fontsize=25, family="sans-serif")
    plt.xticks(fontsize=23)
    plt.yticks(fontsize=23)
    ### Guardo el archivo con la grafica sin bordes
    plt.savefig(filename,bbox_inches='tight')

def main():
    # Parseamos los argumentos
    fromdate, todate, fromdatefortemplate, todatefortemplate, timezone, idproject, apikey, baseurl, stylesheets = parsecliarguments()
    # Sincronizamos con el API de TODOIST
    api = todoist.TodoistAPI(apikey)
    api.sync()
    # Extraemos las tareas completadas
    completedtasks = getCompletedTasks(fromdate,todate,idproject, api)
    # Creamos un dataframe para manipular las tareas completadas
    df_completedtasks = getCompletedTasksDataFrame(completedtasks,timezone)
    # Extraemos las tareas incompletas
    uncompletedtasks = getUncompletedTasks(idproject, api)
    # Creamos un dataframe para manipular las tareas incompletadas
    df_uncompletedtasks = getUncompletedTasksDataframe(uncompletedtasks,timezone)
    # Generamos una grafica pie
    filenamePieChart = "pie.png"
    generatePNGPieChart(filenamePieChart,len(df_completedtasks),len(df_uncompletedtasks))
    # Generamos una grafica barh
    filenameBarhChart = "barh.png"
    generatePNGBarhChart(filenameBarhChart,df_completedtasks)
    # Ya no necesito la columna de FechaCompletada
    df_completedtasks = df_completedtasks[["Id","Tarea","Completada"]]
    df_uncompletedtasks['Creación'] = pd.to_datetime(df_uncompletedtasks["Creación"], format='%Y-%m-%dT%H:%M:%SZ')
    # Obtengo el nobre del proyecto
    projectname = api.projects.get(idproject)
    projectname = projectname["project"]["name"]
    # Cargamos el template
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template("template.html")
    # Alimentamos para el template de HTML
    template_vars = {"titulo" : "Tareas Pendientes",
                    "projectname":projectname,
                    "itemsStatusGeneralChartPie":filenamePieChart,
                    "itemsPendientesChartBarh":filenameBarhChart,
                    "fromdate":fromdatefortemplate,
                    "todate":todatefortemplate,
                    "itemsCompletados":df_completedtasks.to_html(classes="pure-table pure-table-bordered",index=False), 
                    "itemsPendientes": df_uncompletedtasks.to_html(classes="pure-table pure-table-bordered",index=False)}
    html_out = template.render(template_vars)
    # Convertimos el html a un pdf y le pasamos la ruta base de los archivos, imagenes y estilos
    HTML(string=html_out,base_url=baseurl).write_pdf("report_"+str(idproject)+"_"+datetime.now().strftime('%Y_%m_%d_%H_%M_%S')+".pdf", stylesheets=stylesheets)

if __name__ == "__main__":
    main()
