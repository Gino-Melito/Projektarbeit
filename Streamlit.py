import streamlit as st
from influxdb_client import InfluxDBClient, Point
import time

# InfluxDB Verbindungseinstellungen
INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "eE_tQFCYYavWYjM_XVddEniSSJyIACcjsYWPhG6zNZMn2pVL9a_vV5gVlrUYSzE9cjjT5F3-RzYHKL6tPR7L9g=="
INFLUXDB_ORG = "Gino"
INFLUXDB_BUCKET = "Werte_raus_lesen"

# InfluxDB-Client initialisieren
client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = client.write_api()

# Streamlit Benutzeroberfläche
st.title("Haussteuerung")
st.write("Steuere Beleuchtung, Heizung und Garagentor")

# Sidebar für Auswahl von Steuerungsarten
selection = st.sidebar.radio("Steuerung auswählen", ("Lichtsteuerung", "Heizung", "Garagentor"))

if selection == "Lichtsteuerung":
    st.header("Lichtsteuerung")
    
    # Auswahl des Raums für Beleuchtung
    room_for_light = st.selectbox(
        "Wähle einen Raum für die Lichtsteuerung",
        ("Wohnzimmer", "Schlafzimmer", "Eingang", "Keller", "Garage", "Aussenbereich")
    )
    
    # Lichtschalter steuern
    light_on = st.checkbox(f"Licht im {room_for_light} einschalten")
    if light_on:
        st.success(f"Licht im {room_for_light} ist AN 💡")
    else:
        st.warning(f"Licht im {room_for_light} ist AUS ❌")
    
    # Daten direkt in InfluxDB speichern
    point_for_light = (
        Point("raum_steuerung")
        .tag("raum", room_for_light)
        .field("licht_status", int(light_on))
    )
    write_api.write(bucket=INFLUXDB_BUCKET, record=point_for_light)
    st.info(f"Daten für Licht im {room_for_light} gespeichert!")

elif selection == "Heizung":
    st.header("Heizung")
    
    # Auswahl des Raums für Temperatur
    room_for_temp = st.selectbox(
        "Wähle einen Raum für die Temperatursteuerung",
        ("Wohnzimmer", "Schlafzimmer")
    )
    
    # Temperatur einstellen
    temperature = st.slider(
        f"Temperatur im {room_for_temp} einstellen (°C)",
        min_value=0, max_value=100, value=20
    )
    st.info(f"Die Temperatur im {room_for_temp} wurde auf {temperature}°C eingestellt.")

    
    
    # Daten direkt in InfluxDB speichern
    for room in ["Wohnzimmer", "Schlafzimmer"]:
     point_for_temp = (
        Point("raum_steuerung")
        .tag("raum", room_for_temp)
        .field("temperatur",temperature)
    )
    write_api.write(bucket=INFLUXDB_BUCKET, record=point_for_temp)
    st.info(f"Daten für Temperatur im {room_for_temp} gespeichert!")

elif selection == "Garagentor":
    st.header("Wähle die Aktion:")
    action = st.radio("Garagentor:", ["Öffnen", "Schliessen"])

    # Werte für Q4 und Q5 setzen
    status_Q4 = 1 if action == "Öffnen" else 0
    status_Q5 = 1 if action == "Schliessen" else 0
    
    # Beleuchtung P1 nur aktivieren, wenn Tor geöffnet oder geschlossen wird
    status_P1 = 1 if action in ["Öffnen", "Schliessen"] else 0  # Beleuchtung P1 aktivieren

    if st.button("Steuern"):
    # Daten für P1 in separatem Feld speichern
        point = (
            Point("raum_steuerung")
            .tag("raum", "Garage")
            .field("tor_status_Q4", status_Q4)  # Feld für Q4 (Öffnen)
            .field("tor_status_Q5", status_Q5)  # Feld für Q5 (Schließen)
            .field("licht_status_P1", status_P1)  # P1 Beleuchtung separat behandeln
        )
        write_api.write(bucket=INFLUXDB_BUCKET, record=point)
    
        # Warte 10 Sekunden und setze P1 auf 0 zurück
        time.sleep(20)

        # Setze P1 auf 0 und speichere in InfluxDB
        point_P1_off = (
            Point("raum_steuerung")
            .tag("raum", "Garage")
            .field("licht_status_P1", 0)  # Beleuchtung P1 deaktivieren
        )
        write_api.write(bucket=INFLUXDB_BUCKET, record=point_P1_off)





    # Erfolgsnachricht
    st.success(f"Garagentor '{action}' erfolgreich gesteuert und Beleuchtung aktiviert.")
    
    # Verbindung schließen
    client.close()

