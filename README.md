Proyecto de Scraping 9Now
Este proyecto realiza scraping de la página de 9Now mediante Peticiones HTTP y Playwright, extrayendo información de diferentes secciones (Live TV, Featured, Live Channels, Tab 4 y Categorías) y combinándola con datos adicionales de una API para enriquecer cada entrada con campos como descripción, canal, género y hora.

Funcionalidades
Extracción de datos HTML: Se utiliza Playwright para recorrer las páginas y extraer datos visuales como el título, imagen, canal, horarios, etc.
Integración con API: Se realizan peticiones a la API de 9Now para obtener datos adicionales (como la descripción y destinationUri) y se combinan con la información extraída.
Actualización y ordenamiento: Se comparan y actualizan los datos extraídos de la página con los datos de la API mediante un proceso recursivo. Además, los resultados se ordenan según un criterio definido.
Monitoreo de recursos: Al final del proceso se muestran estadísticas de uso de CPU y RAM.

Tecnologías utilizadas:

Python 3.10+

Playwright: Para la automatización del navegador.

aiohttp: Para realizar peticiones asíncronas a la API.

Pandas: Para el manejo de archivos CSV.

Psutil: Para monitorear el uso de CPU y RAM.

Asyncio: Para la programación asíncrona.

Explicaciones de los datos: 

URLS.cvs carga de url y url_type donde se carga cualquier url de la pagina con su respectivo type ("category","Keyword","Home",etc)

Extracted_9now.json = json donde se carga toda la data con su tiempo de ejecucion , uso de ram , cpu y fecha de registro ademas carga el type explicado anteriormente.

9now_ua.py = codigo diseño para hacer scraping completo a 9now.

tabs.json = almacena todo los datos de la api donde es consumido por 9now_ua.py

Grabacion de pantalla donde se muestra el scraping respectivo para obtener la screenshot y la carga completa de las api.
https://drive.google.com/file/d/1EDdoSP7CqzhEWe-b28OhsLlRcE545Tu4/view?usp=sharing
