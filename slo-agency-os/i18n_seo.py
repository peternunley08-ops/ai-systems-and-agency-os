#!/usr/bin/env python3
"""
i18n_seo.py  —  V5 helpers for generate_mockups.py
==================================================
Two functions, kept in their own module so the main generator stays small:

  jsonld(lead)        -> a <script type="application/ld+json"> LocalBusiness block
                         for local SEO. aggregateRating is included ONLY when the
                         lead has a real rating AND review count (never faked).

  i18n_map(ctx, content) -> an EN->ES dictionary the mockup uses for a live
                         language toggle. The toggle matches visible text nodes by
                         their exact English string, so this map just needs to list
                         every English phrase that should switch to Spanish.

NOTE ON TRANSLATIONS: the UI labels are translated accurately. Marketing body copy
(taglines, service blurbs, sample testimonials) is translated too, but a native
speaker should proof it before a site goes live.
"""

from __future__ import annotations

import json
import re

# --------------------------------------------------------------------------- #
# JSON-LD structured data
# --------------------------------------------------------------------------- #
_SCHEMA_TYPE = {
    "food truck": "FoodEstablishment",
    "bakery": "Bakery",
    "handyman": "HomeAndConstructionBusiness",
    "landscaping": "HomeAndConstructionBusiness",
    "plumber": "Plumber",
    "roofer": "RoofingContractor",
    "painter": "HousePainter",
    "pet groomer": "LocalBusiness",
}


def jsonld(lead: dict, services: list | None = None) -> str:
    name = (lead.get("business_name") or "").strip()
    city = (lead.get("city") or "").strip()
    phone = (lead.get("phone") or "").strip()
    niche = (lead.get("niche") or "").strip().lower()
    if not name:
        return ""
    data = {
        "@context": "https://schema.org",
        "@type": _SCHEMA_TYPE.get(niche, "LocalBusiness"),
        "name": name,
        "priceRange": "$$",
    }
    _area = []
    for _a in [city, "San Luis Obispo County", "Paso Robles", "Atascadero",
               "San Luis Obispo", "Morro Bay", "Los Osos", "Pismo Beach",
               "Arroyo Grande", "Nipomo", "Templeton", "Santa Maria"]:
        if _a and _a not in _area:
            _area.append(_a)
    data["areaServed"] = _area
    addr = (lead.get("address") or "").strip()
    if addr:
        data["address"] = {
            "@type": "PostalAddress", "streetAddress": addr,
            "addressLocality": city, "addressRegion": "CA", "addressCountry": "US",
        }
        _zip = re.search(r"\b(\d{5})\b", addr)
        if _zip:
            data["address"]["postalCode"] = _zip.group(1)
    if phone:
        data["telephone"] = phone
    src = (lead.get("source_url") or "").strip()
    if src:
        data["sameAs"] = [src]
    # url / image: emitted ONLY when real values exist (never fabricated).
    # These businesses have no site yet, so url is normally empty; once the new
    # site is live, set lead["url"] (and lead["image"]) and it flows through here.
    url = (lead.get("url") or "").strip()
    if url and not url.startswith("["):
        data["url"] = url
    img = (lead.get("image") or "").strip()
    if img and not img.startswith("["):
        data["image"] = img
    lat = (lead.get("lat") or "").strip()
    lng = (lead.get("lng") or "").strip()
    if lat and lng:  # only when find_leads.py captured real Places coordinates
        data["geo"] = {"@type": "GeoCoordinates", "latitude": lat, "longitude": lng}
    rating = (lead.get("rating") or "").strip()
    reviews = (lead.get("review_count") or "").strip()
    if rating and reviews:  # only emit review markup when it is real
        data["aggregateRating"] = {
            "@type": "AggregateRating", "ratingValue": rating,
            "reviewCount": reviews, "bestRating": "5",
        }
    # makesOffer: the same service categories shown on the page, expressed as
    # schema.org Offers/Services for richer local search. Consistent with on-page
    # content (no new claims). `services` is the niche's svc list of
    # (icon, title, desc) tuples passed by the generator.
    if services:
        offers = []
        for _svc in services:
            if len(_svc) >= 3:
                _t, _d = _svc[1], _svc[2]
            elif len(_svc) == 2:
                _t, _d = _svc[0], _svc[1]
            else:
                continue
            _t = (_t or "").strip()
            if not _t:
                continue
            _item = {"@type": "Service", "name": _t}
            _d = (_d or "").strip()
            if _d:
                _item["description"] = _d
            offers.append({"@type": "Offer", "itemOffered": _item})
        if offers:
            data["makesOffer"] = offers
    return ('<script type="application/ld+json">\n'
            + json.dumps(data, ensure_ascii=False, indent=2)
            + "\n</script>")


# --------------------------------------------------------------------------- #
# Spanish translations
# --------------------------------------------------------------------------- #
ES_BY_NICHE = {
    "food truck": {
        "tag": "Comida callejera que vale la pena perseguir.",
        "sub": "Favoritos frescos, hechos al momento y servidos calientes desde nuestro camión — ahora reservables en línea para tu próximo evento.",
        "cta": "Reserva el Camión",
        "svc": [
            ("El Menú", "Cada taco, plato y especial: míralo antes de llegar."),
            ("Banquetes para Eventos", "Bodas, fiestas y almuerzos corporativos, con personal completo."),
            ("Encuentra el Camión", "Un horario semanal en vivo para que los clientes siempre te localicen."),
            ("Reservas Privadas", "Reserva el camión para tu evento en dos toques."),
            ("Ordena con Anticipación", "Evita la fila pidiendo para recoger."),
            ("Favoritos del Público", "Los platillos por los que la gente hace fila, al frente."),
        ],
        "rev": ["Lo mejor de la Costa Central", "Atendieron nuestra boda", "Un ritual semanal"],
    },
    "handyman": {
        "tag": "Tu lista de pendientes, resuelta.",
        "sub": "Reparaciones del hogar confiables y con licencia en toda la Costa Central. Presupuestos gratis, trabajo limpio, bien hecho a la primera.",
        "cta": "Pide un Presupuesto Gratis",
        "svc": [
            ("Reparaciones y Mantenimiento", "Desde llaves que gotean hasta puertas atascadas: una llamada lo resuelve."),
            ("Tablaroca y Pintura", "Resane, textura y pintura que combinan a la perfección."),
            ("Carpintería", "Molduras, repisas, terrazas y muebles a medida."),
            ("Instalación de Accesorios", "Lámparas, ventiladores, llaves, televisores y herrajes montados con seguridad."),
            ("Cercas y Portones", "Reparaciones e instalaciones nuevas hechas para la costa."),
            ("Presupuestos Gratis", "Cotizaciones por escrito y transparentes antes de empezar."),
        ],
        "rev": ["Me salvó el fin de semana", "Honesto y puntual", "Mi opción para todo"],
    },
    "pet groomer": {
        "tag": "Estética que llega a tu puerta.",
        "sub": "Estética móvil sin jaulas y personalizada en la puerta de tu casa — menos estrés para tu mascota y sin manejar para ti.",
        "cta": "Reserva una Cita",
        "svc": [
            ("Estética Completa", "Corte según la raza, estilo y toques finales."),
            ("Baño y Cepillado", "Limpieza profunda, pelaje acondicionado, uñas y orejas."),
            ("Cuidado de Uñas y Patas", "Corte y limado sin la lucha."),
            ("Control de Muda", "Elimina el subpelo suelto y mantén tu hogar sin pelos."),
            ("Servicio Móvil", "El salón llega a tu cochera, totalmente equipado."),
            ("Reservas Recurrentes", "Programa citas recurrentes para que siempre luzcan frescos."),
        ],
        "rev": ["A mi perro le encanta", "Muy conveniente", "Gentil con los mayores"],
    },
    "landscaping": {
        "tag": "Belleza exterior, temporada tras temporada.",
        "sub": "Diseño, construcción y mantenimiento de jardines de la Costa Central que ahorran agua y lucen increíbles.",
        "cta": "Solicita una Cotización",
        "svc": [
            ("Diseño de Jardines", "Diseños duraderos, tolerantes a la sequía y con plantas nativas."),
            ("Obra Dura", "Adoquines, senderos, muros de contención y patios."),
            ("Riego", "Sistemas eficientes que reducen tu factura de agua."),
            ("Mantenimiento", "Planes de cuidado semanales y quincenales confiables."),
            ("Limpiezas", "Renovación de temporada, acarreo y preparación para tormentas."),
            ("Visitas Gratis", "Presupuestos en sitio con precios claros."),
        ],
        "rev": ["Transformaron nuestro jardín", "Equipo confiable", "Bajó la factura de agua"],
    },
}

ES_DEFAULT = {
    "tag": "Servicio local en el que puedes confiar.",
    "sub": "Servicio profesional y confiable en todo el condado de San Luis Obispo — ahora fácil de encontrar y reservar en línea.",
    "cta": "Ponte en Contacto",
    "svc": [
        ("Trabajo de Calidad", "Bien hecho, a tiempo, siempre."),
        ("Reserva Fácil", "Contáctanos con un toque desde cualquier dispositivo."),
        ("Servicio 5 Estrellas", "La reputación que tus clientes ya te dan."),
        ("Respuesta Rápida", "Cotizaciones rápidas y agenda puntual."),
        ("Con Licencia y Confiable", "Local, asegurado y responsable."),
        ("Servimos la Costa", "Orgullosamente local del condado SLO."),
    ],
    "rev": ["Muy recomendable", "Gran experiencia", "Volveré a usarlo"],
}

# Sample testimonial bodies (must match generate_mockups.reviews_block, decoded).
_REV_BODIES_EN = [
    "Showed up exactly when they said, did beautiful work, and the price matched the quote. Couldn't ask for more.",
    "Friendly, professional, and clearly knows their craft. I've already recommended them to two neighbors.",
    "Easy to book, great communication, and the results speak for themselves. This is who I'll call from now on.",
]
_REV_BODIES_ES = [
    "Llegaron justo cuando dijeron, hicieron un trabajo hermoso y el precio coincidió con la cotización. No se puede pedir más.",
    "Amables, profesionales y claramente dominan su oficio. Ya los recomendé a dos vecinos.",
    "Fácil de reservar, excelente comunicación y los resultados hablan por sí solos. A ellos llamaré de ahora en adelante.",
]



ES_BY_NICHE["tree service"] = {
    "tag": "Tus árboles, en manos expertas.",
    "sub": "Cuidado de árboles con licencia y seguro en toda la Costa Central - poda, remoción y respuesta a tormentas 24/7, con seguridad y limpieza.",
    "cta": "Pide un Presupuesto Gratis",
    "svc": [
        ("Poda de Árboles", "Formado y aclareo de copa que mantiene los árboles sanos y seguros."),
        ("Remoción de Árboles", "Remoción segura y eficiente de árboles peligrosos o no deseados."),
        ("Triturado de Tocones", "Trituramos tocones bajo el nivel del suelo y recuperas tu jardín."),
        ("Emergencias y Tormentas", "Respuesta 24/7 para ramas caídas y daños por tormenta."),
        ("Limpieza de Lotes y Maleza", "Limpieza de maleza y espacio defensible contra incendios."),
        ("Presupuestos Gratis", "Cotizaciones honestas por escrito antes de empezar."),
    ],
    "rev": ["Salvaron nuestro roble", "Limpieza rápida tras la tormenta", "Justos y profesionales"],
}
ES_BY_NICHE["house cleaning"] = {
    "tag": "Un hogar impecable, siempre.",
    "sub": "Limpieza del hogar confiable y meticulosa en toda la Costa Central - recurrente, profunda y de mudanza, por un equipo en quien puedes confiar.",
    "cta": "Pide una Cotización Gratis",
    "svc": [
        ("Limpieza Recurrente", "Visitas semanales, quincenales o mensuales que lo hacen fácil."),
        ("Limpieza Profunda", "Detalle de arriba a abajo: zócalos, accesorios, todo."),
        ("Mudanza de Entrada/Salida", "Recupera tu depósito o empieza en un espacio impecable."),
        ("Confiable y Asegurado", "Personal verificado, asegurado y consistente."),
        ("Agenda Fácil", "Reserva y reprograma con un toque; sin contratos."),
        ("Garantía de Satisfacción", "¿Un punto no quedó bien? Lo corregimos."),
    ],
    "rev": ["Mi casa nunca estuvo tan limpia", "Confiables y de fiar", "Vale cada centavo"],
}


def _es(niche: str) -> dict:
    return ES_BY_NICHE.get((niche or "").strip().lower(), ES_DEFAULT)


def i18n_map(ctx: dict, content: dict) -> dict:
    """Build the EN->ES lookup for the live language toggle. Keys are the exact
    visible English strings as they render (HTML entities already decoded)."""
    es = _es(ctx["niche"])
    city = ctx.get("city", "")
    name = ctx.get("name", "")
    phone = ctx.get("phone", "")
    m: dict[str, str] = {}

    # nav + chrome
    m["Services"] = "Servicios"
    m["Reviews"] = "Reseñas"
    m["Contact"] = "Contacto"
    m["See services"] = "Ver servicios"
    m["Explore services"] = "Ver servicios"
    m["Book now"] = "Reservar ahora"
    m["Ask about this"] = "Pregunta por esto"
    # stats
    m["Avg rating"] = "Calificación"
    m["Serving"] = "Atendemos"
    m["Quotes"] = "Cotizaciones"
    m["Same-day"] = "Mismo día"
    # hero B action cells
    m["Call / Text"] = "Llamar / Mensaje"
    m["Hours"] = "Horario"
    m["Service area"] = "Zona de servicio"
    m["Reputation"] = "Reputación"
    m["Tap to contact"] = "Toca para contactar"
    m["Locally loved"] = "Muy querido localmente"

    # CTA buttons (with and without phone suffix)
    def cta(label_en: str, label_es: str):
        m[label_en] = label_es
        if phone:
            m[f"{label_en} · {phone}"] = f"{label_es} · {phone}"
    cta(content["cta"], es["cta"])
    cta("Call now", "Llamar ahora")
    # conversion bar
    m["Contact us"] = "Contáctanos"
    if phone:
        m[f"Call {phone}"] = f"Llamar {phone}"

    # hero copy
    m[content["tag"]] = es["tag"]
    m[content["sub"]] = es["sub"]

    # services section
    m["What we do"] = "Lo que hacemos"
    m[f"Everything {city} relies on us for"] = f"Todo aquello en lo que {city} confía en nosotros"
    m["Clear services, honest pricing, and a booking experience your customers will actually enjoy."] = \
        "Servicios claros, precios honestos y una experiencia de reserva que tus clientes disfrutarán."
    for (en_t, en_d), (es_t, es_d) in zip(
            [(t, d) for _, t, d in content["svc"]], es["svc"]):
        m[en_t] = es_t
        m[en_d] = es_d

    # reviews section
    m["What our customers say"] = "Lo que dicen nuestros clientes"
    m[f"Loved by neighbors across {city}"] = f"Querido por los vecinos de {city}"
    m["Your reputation is your best marketing - we put it where everyone can see it."] = \
        "Tu reputación es tu mejor publicidad: la ponemos donde todos puedan verla."
    for en_b, es_b in zip(_REV_BODIES_EN, _REV_BODIES_ES):
        m["“" + en_b + "”"] = "“" + es_b + "”"
    for en_t, es_t in zip(content["rev"], es["rev"]):
        m[f"{en_t} · Sample testimonial"] = f"{es_t} · Testimonio de muestra"

    # contact section
    m["Get in touch"] = "Ponte en contacto"
    m["Ready when you are"] = "Listos cuando tú lo estés"
    m[f"Send a request and {name} will get right back to you. No phone tag, no hold music."] = \
        f"Envía una solicitud y {name} te responderá enseguida. Sin llamadas perdidas ni música de espera."
    m["Call or text for a fast quote"] = "Llama o envía un mensaje para una cotización rápida"
    m[f"Serving {city} & the Central Coast"] = f"Atendemos {city} y la Costa Central"
    m[f"{city} · same-day estimates"] = f"{city} · presupuestos el mismo día"
    # form
    m["Your name"] = "Tu nombre"
    m["Phone or email"] = "Teléfono o correo"
    m["What do you need?"] = "¿Qué necesitas?"
    m["Details"] = "Detalles"
    m["Request a quote"] = "Solicitar cotización"
    m["Book a service"] = "Reservar un servicio"
    m["Ask a question"] = "Hacer una pregunta"
    m["Catering / event"] = "Banquete / evento"
    m["Jane Doe"] = "Juan Pérez"
    m["Tell us a little about the job..."] = "Cuéntanos un poco sobre el trabajo..."

    # drop any accidental identity mappings
    return {k: v for k, v in m.items() if k and v and k != v}
