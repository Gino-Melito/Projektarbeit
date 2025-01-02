import socket
import time
from influxdb_client import InfluxDBClient

# InfluxDB Verbindungseinstellungen
INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "eE_tQFCYYavWYjM_XVddEniSSJyIACcjsYWPhG6zNZMn2pVL9a_vV5gVlrUYSzE9cjjT5F3-RzYHKL6tPR7L9g=="
INFLUXDB_ORG = "Gino"
INFLUXDB_BUCKET = "Werte_raus_lesen"

# UDP-Verbindungseinstellungen
UDP_IP = "127.0.0.1"  # IP der Steuerung
ports = {
    # Wohnzimmer
    "E3": 1709,
    "B5": 1604,  # Raumtemperatur istwert
    "B4": 1603,  # Raumtemperatur sollwert
    "M1": 1717,  # Ventil Öffnung in % (100% = 1000)
    # Schlafzimmer
    "E1": 1716,  # Beleuchtung dimmbar 100% = 1000)
    # Eingang
    "E4": 1710,  # Außenlampe Haustür
    "Q1": 1700,  # Storen öffnen
    "Q2": 1701,  # Storen schliessen
    # Keller
    "E2": 1711,  # Keller Licht
    # Garage
    "P1": 1713,  # Warnleuchte Garage
    "E6": 1714,  # Garage Beleuchtung
    "Q4": 1703,  # Tor öffnen
    "Q5": 1704,  # Tor schließen
    # Außenbereich
    "B1": 1600,  # Helligkeit
    "B2": 1601,  # Windstärke
    "B3": 1602,  # Regenmenge
    "E5": 1712,  # Garten Beleuchtung
    "Q7": 1706,  # Markisen einfahren
    "Q8": 1707,  # Markisen ausfahren
}

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# InfluxDB-Client initialisieren
client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
query_api = client.query_api()

# Funktion zur Abfrage des aktuellen Lichtstatus von P1 in der Garage aus InfluxDB
def get_p1_light_status():
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r["_measurement"] == "raum_steuerung")
      |> filter(fn: (r) => r["raum"] == "Garage")
      |> filter(fn: (r) => r["_field"] == "licht_status_P1")
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: 1)
    '''
    result = query_api.query(org=INFLUXDB_ORG, query=query)
    p1_status = None

    for table in result:
        for record in table.records:
            if record["_field"] == "licht_status_P1":
                p1_status = record["_value"]
                
    print(f"Lichtstatus von P1 (Garage): {p1_status}")
    return p1_status

# Funktion zum Senden des Garagentorbefehl (E6 Licht ein-/ausschalten)
def send_garage_light_on():
    message = "1"  # 1 bedeutet Licht einschalten
    sock.sendto(message.encode(), (UDP_IP, ports["E6"]))  # Befehl an E6 senden
    print(f"Befehl zum Einschalten von Garagebeleuchtung (E6) gesendet: {message}")

def send_garage_light_off():
    message = "0"  # 0 bedeutet Licht ausschalten
    sock.sendto(message.encode(), (UDP_IP, ports["E6"]))  # Befehl an E6 senden
    print(f"Befehl zum Ausschalten von Garagebeleuchtung (E6) gesendet: {message}")

# Funktion zur Steuerung des Garagentors und Beleuchtung P1
def send_garage_command(command):
    if command == "open":
        # Setze Q4 auf 1 und Q5 auf 0
        sock.sendto(b"1", (UDP_IP, ports["Q4"]))  # Tor öffnen (Q4)
        sock.sendto(b"0", (UDP_IP, ports["Q5"]))  # Tor schliessen (Q5)
        print("Tor öffnet sich.")
        # Beleuchtung P1 aktivieren
        p1_status = get_p1_light_status()
        if p1_status == 1:
            sock.sendto(b"1", (UDP_IP, ports["P1"]))  # Garage Beleuchtung P1 einschalten
            print("Beleuchtung P1 aktiviert, da das Tor geöffnet wird.")
    elif command == "close":
        # Setze Q5 auf 1 und Q4 auf 0
        sock.sendto(b"0", (UDP_IP, ports["Q4"]))  # Tor öffnen (Q4)
        sock.sendto(b"1", (UDP_IP, ports["Q5"]))  # Tor schliessen (Q5)
        print("Tor schliesst sich.")
        # Beleuchtung P1 aktivieren
        p1_status = get_p1_light_status()
        if p1_status == 1:
            sock.sendto(b"1", (UDP_IP, ports["P1"]))  # Garage Beleuchtung P1 einschalten
            print("Beleuchtung P1 aktiviert, da das Tor geschlossen wird.")

        # Nach 10 Sekunden Beleuchtung P1 ausschalten
    time.sleep(10)
    sock.sendto(b"0", (UDP_IP, ports["P1"]))  # Beleuchtung P1 ausschalten
    print("Beleuchtung P1 wurde nach 10 Sekunden deaktiviert.")


# Funktion zur Abfrage der neuesten Daten für einen Raum
def get_latest_room_data(raum_control):
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r["_measurement"] == "raum_steuerung")
      |> filter(fn: (r) => r["raum"] == "{raum_control}")
      |> filter(fn: (r) => r["_field"] == "licht_status" or r["_field"] == "temperatur")
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: 1)
    '''
    result = query_api.query(org=INFLUXDB_ORG, query=query)

    licht_status = None
    temperatur = None

    for table in result:
        for record in table.records:
            if record["_field"] == "licht_status":
                licht_status = record["_value"]
            elif record["_field"] == "temperatur":
                temperatur = record["_value"]

    return {"licht_status": licht_status, "temperatur": temperatur}


# Funktion zur Abfrage des Sollwertes B4 (Temperatur)
def get_b4_temperature():
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r["_measurement"] == "raum_steuerung")
      |> filter(fn: (r) => r["raum"] == "Wohnzimmer" or r["raum"] == "Schlafzimmer")
      |> filter(fn: (r) => r["_field"] == "temperatur")
      |> group(columns: ["raum"])  // Gruppierung nach Raum
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: 1)
    '''
    result = query_api.query(org=INFLUXDB_ORG, query=query)
    temperatur_b4_wz = None
    temperatur_b4_sz = None

    # Durchlaufen der Abfrageergebnisse
    for table in result:
        for record in table.records:
            if record["raum"] == "Wohnzimmer" and record["_field"] == "temperatur":
                temperatur_b4_wz = record["_value"]
            elif record["raum"] == "Schlafzimmer" and record["_field"] == "temperatur":
                temperatur_b4_sz = record["_value"]
    
    return temperatur_b4_wz, temperatur_b4_sz

# Funktion zur Steuerung des Ventils M1 basierend auf dem Sollwert B4
def control_ventil_m1(sollwert):
    # Simpler Regelmechanismus: Mehr Öffnung bei grosser Abweichung
    venti_offnung = min(1000, max(0, 1000 * (sollwert / 100)))  # Skalierung 1000 = 100%
    sock.sendto(str(int(venti_offnung)).encode(), (UDP_IP, ports["M1"]))
    print(f"Ventil M1 auf {venti_offnung / 10}% geöffnet.")


# Haupt-Loop
try:
    while True:
        # Steuerung der Garage basierend auf Torstatus (Q4 und Q5)
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -5m)
          |> filter(fn: (r) => r["_measurement"] == "raum_steuerung")
          |> filter(fn: (r) => r["raum"] == "Garage")
          |> last()
        '''
        result = query_api.query(org=INFLUXDB_ORG, query=query)
        garage_status = {"tor_status_Q4": 0, "tor_status_Q5": 0}

        for table in result:
            for record in table.records:
                field = record.get_field()
                value = record.get_value()
                garage_status[field] = value  # Werte für Q4 und Q5 speichern

        print("Aktueller Garagentor-Status:", garage_status)

        # Garagentorsteuerung
        if garage_status["tor_status_Q4"] == 1 and garage_status["tor_status_Q5"] == 0:
            print("Tor öffnen...")
            send_garage_command("open")
        elif garage_status["tor_status_Q5"] == 1 and garage_status["tor_status_Q4"] == 0:
            print("Tor schliessen...")
            send_garage_command("close")
        else:
            print("Kein aktiver Garagentor-Befehl. Beide Schütze müssen separat gesetzt werden.")

        # Liste der Räume
        räume = {
            "Wohnzimmer": {"licht": "E3", "temperatur": "M1"},
            "Keller": {"licht": "E2"},
            "Schlafzimmer": {"licht": "E3"},
            "Eingang": {"licht": "E4"},
            "Garage": {"licht": "E6"},  
            "Aussenbereich": {"licht": "E5"},
        }

        for raum_name, ports_map in räume.items():
            data = get_latest_room_data(raum_name)
            print(f"{raum_name}: {data}")

            if data:
                # Lichtstatus senden
                if data["licht_status"] is not None:
                    licht_status = "1" if data["licht_status"] == 1 else "0"
                    # Stelle sicher, dass E6 nicht durch das Tor gesteuert wird
                    sock.sendto(licht_status.encode(), (UDP_IP, ports[ports_map["licht"]]))
                    print(f"Lichtstatus für {raum_name} gesendet: {licht_status}")

                # Temperatur senden (falls verfügbar)
                if "temperatur" in ports_map and data["temperatur"] is not None:
                    temperatur_wert = str(data["temperatur"]).encode("utf-8")
                    sock.sendto(temperatur_wert, (UDP_IP, ports[ports_map["temperatur"]]))
                    print(f"Temperatur für {raum_name} gesendet: {temperatur_wert}")



# B4-Wert (Sollwert) aus InfluxDB abfragen
        b4_temp_wz, b4_temp_sz = get_b4_temperature()
        
        if b4_temp_wz is not None and b4_temp_sz is not None:
            # Bestimme den höchsten Wert aus beiden
            max_b4_temp = max(b4_temp_wz, b4_temp_sz)
            
            print(f"Sollwert B4 Wohnzimmer: {b4_temp_wz}°C")
            print(f"Sollwert B4 Schlafzimmer: {b4_temp_sz}°C")
            print(f"Höchster Sollwert für M1: {max_b4_temp}°C")

            # Steuerung des Ventils basierend auf dem höchsten Sollwert
            control_ventil_m1(max_b4_temp)  # Ventilsteuerung mit dem höchsten Wert
        else:
            print("B4-Wert konnte nicht abgerufen werden.")

        time.sleep(5)  # Alle 5 Sekunden Daten abrufen und senden

except KeyboardInterrupt:
    print("\nProgramm beendet.")
    sock.close()
    client.close()






































