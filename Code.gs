/**
 * Link de reseña para carteles NFC.
 *
 * Publicar (una sola vez):
 * 1. Entrá a https://script.google.com y creá un proyecto nuevo.
 * 2. Pegá este archivo en Code.gs (reemplazá el contenido).
 * 3. Archivo → Nuevo → Archivo HTML. Nombralo exactamente Index.
 *    Pegá ahí el contenido de Index.html.
 * 4. En Google Cloud habilitá "Places API (New)" y creá una API key.
 *    Restringila solo a Places API (New). No la restrinjas por sitio web
 *    ni por IP: Apps Script llama a Google desde sus servidores.
 * 5. En Apps Script: Configuración del proyecto → Propiedades del script
 *    → Agregar propiedad. Nombre: GOOGLE_MAPS_API_KEY. Valor: la key.
 * 6. Implementar → Nueva implementación → Aplicación web.
 *    Ejecutar como: Yo. Quién tiene acceso: Solo yo.
 * 7. Si cambiás el código, actualizá esa implementación a una versión nueva.
 * 8. Abrí la URL /exec en el celular, con la misma cuenta Google.
 */
function doGet(e) {
  var nombre = param(e, 'nombre');
  var calle = param(e, 'calle');
  var busco = param(e, 'busco') === '1';
  var datos = {
    scriptUrl: ScriptApp.getService().getUrl() || '',
    nombre: nombre,
    calle: calle,
    error: '',
    lugares: []
  };

  if (busco && nombre.length < 2) {
    datos.error = 'Escribí el nombre del lugar.';
  } else if (busco) {
    try {
      datos.lugares = buscarLugares(armarConsulta(nombre, calle));
      if (!datos.lugares.length) {
        datos.error = 'No encontré ese lugar. Probá agregando la calle.';
      }
    } catch (err) {
      datos.error = err && err.message ? err.message : 'No se pudo buscar.';
    }
  }

  var page = HtmlService.createHtmlOutputFromFile('Index').getContent();
  page = page.replace('var DATOS = null;', 'var DATOS = ' + jsonParaScript(datos) + ';');

  return HtmlService.createHtmlOutput(page)
    .setTitle('Link de reseña')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function jsonParaScript(data) {
  return JSON.stringify(data)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026');
}

function param(e, name) {
  if (!e || !e.parameter || e.parameter[name] == null) return '';
  var value = e.parameter[name];
  if (Object.prototype.toString.call(value) === '[object Array]') value = value[0];
  return String(value).replace(/^\s+|\s+$/g, '');
}

function armarConsulta(nombre, calle) {
  nombre = String(nombre || '').trim();
  calle = String(calle || '').trim();
  var consulta = calle ? nombre + ', ' + calle : nombre;
  return consulta.slice(0, 200);
}

function buscarLugares(consulta) {
  consulta = String(consulta || '').trim();
  if (consulta.length < 2) {
    throw new Error('Escribí el nombre del lugar.');
  }
  consulta = consulta.slice(0, 200);

  var key = PropertiesService.getScriptProperties().getProperty('GOOGLE_MAPS_API_KEY');
  if (!key) {
    throw new Error('Falta la API key. En Apps Script: Configuración del proyecto → Propiedades del script → GOOGLE_MAPS_API_KEY.');
  }

  var response;
  try {
    response = UrlFetchApp.fetch('https://places.googleapis.com/v1/places:searchText', {
      method: 'post',
      contentType: 'application/json',
      headers: {
        'X-Goog-Api-Key': key,
        'X-Goog-FieldMask': 'places.id,places.displayName,places.formattedAddress'
      },
      payload: JSON.stringify({
        textQuery: consulta,
        languageCode: 'es',
        regionCode: 'AR',
        maxResultCount: 5
      }),
      muteHttpExceptions: true
    });
  } catch (e) {
    throw new Error('No se pudo conectar con Google. Revisá la API key y que Places API (New) esté habilitada.');
  }

  var raw = response.getContentText();
  var body;
  try {
    body = JSON.parse(raw);
  } catch (e) {
    throw new Error('Google respondió algo inesperado.');
  }

  var status = response.getResponseCode();
  if (status !== 200) {
    throw new Error(mensajeError(status, body));
  }

  return (body.places || []).filter(function (place) {
    return place && place.id;
  }).map(function (place) {
    var nombre = place.displayName && place.displayName.text
      ? place.displayName.text
      : 'Sin nombre';
    return {
      id: place.id,
      nombre: nombre,
      direccion: place.formattedAddress || '',
      url: 'https://search.google.com/local/writereview?placeid=' + place.id
    };
  });
}

function mensajeError(status, body) {
  var msg = body && body.error && body.error.message ? body.error.message : '';
  if (status === 403 || /API key|permission|blocked/i.test(msg)) {
    return 'La API key no sirve o falta habilitar Places API (New) en Google Cloud.';
  }
  if (status === 400) {
    return 'Google no pudo buscar ese lugar. Probá agregando la calle.';
  }
  return msg || 'No se pudo buscar. Probá de nuevo.';
}
