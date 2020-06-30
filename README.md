# TodoistProjectToPDF

Convierte un proyecto de todoist a un pdf con gráficas y estus del mismo

## Instalación
```
> git clone https://github.com/jarinlima/TodoistProjectToPDF.git
```

```
> pip install -r requirements.txt
```
## Ejemplo

```
> python .\todoistProjectReport.py --todate="now" --fromdate="-7d" --idproject=1234567891 --apikey=ad554ad5a0da548fas5465aa4s8fa --timezone="America/Guatemala"
```
Esto generará un archivo llamado report.pdf

## Más detalles en este post
https://blog.jarinlima.com/2020/06/30/generar-un-reporte-en-pdf-de-todoist-con-python-weasyprint-y-jinja/