#include <Ethernet.h>

// ============================================================================
// PINES
// ============================================================================
#define PIN_SAFE       I1_2      // Seta: HIGH = NO pulsada, LOW = pulsada
#define PIN_REF_X      I1_4      // X referenciado (dryve D1)
#define PIN_LAMPARAS   A0_0      // Salida 0-10 V (analogWrite 0..255)
#define PIN_PRINT_PULSE R1_4     // Pulso de arranque de impresion

#define LAMPARAS_MAX 255
#define DURACION_PULSO_PRINT_MS 300

// ============================================================================
// BANCO DE PRUEBAS
// ============================================================================
// true  = la seta se considera SIEMPRE liberada (no hay seta instalada)
// false = se lee I1_2 de verdad
// ¡¡¡ PONER A false AL MONTAR LA SETA !!!
#define SIMULAR_SETA_LIBERADA true

// ============================================================================
// RED
// ============================================================================
byte mac[] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0x02};
IPAddress ip(192, 168, 79, 180);    // IP del M-Duino
#define PUERTO_TCP 5000

EthernetServer server(PUERTO_TCP);
EthernetClient cliente;
String bufferRx = "";

// ============================================================================
// ESTADO
// ============================================================================
int valor_lamparas = 0;
bool seta_anterior = false;
bool ref_x_anterior = false;

bool pulso_print_activo = false;
unsigned long t_inicio_pulso = 0;

unsigned long ultimo_envio_periodico = 0;
#define INTERVALO_PERIODICO_MS 1000

////////////////////////////////////////////////////////////////////////////////////////////////////
void setup() {
  Serial.begin(9600);
  delay(500);
  Serial.println();
  Serial.println("=== INICIANDO M-DUINO (servidor TCP) ===");

  pinMode(PIN_SAFE, INPUT);
  pinMode(PIN_REF_X, INPUT);
  pinMode(PIN_LAMPARAS, OUTPUT);
  analogWrite(PIN_LAMPARAS, 0);
  pinMode(PIN_PRINT_PULSE, OUTPUT);
  digitalWrite(PIN_PRINT_PULSE, LOW);

  Ethernet.begin(mac, ip);
  while (Ethernet.localIP() == IPAddress(0, 0, 0, 0)) {
    Serial.println("Esperando conexion de red...");
    delay(1000);
  }

  server.begin();
  Serial.print("Servidor TCP en ");
  Serial.print(Ethernet.localIP());
  Serial.print(":");
  Serial.println(PUERTO_TCP);
}
////////////////////////////////////////////////////////////////////////////////////////////////////
void loop() {
  // Aceptar cliente (Python) si no hay uno conectado
  if (!cliente || !cliente.connected()) {
    EthernetClient nuevo = server.available();
    if (nuevo) {
      cliente = nuevo;
      bufferRx = "";
      Serial.println("Cliente conectado");
      enviarSeta(true);
      enviarRef(true);
    }
  }

  // Leer lineas entrantes
  if (cliente && cliente.connected()) {
    while (cliente.available()) {
      char c = cliente.read();
      if (c == '\n') {
        procesarLinea(bufferRx);
        bufferRx = "";
      } else if (c != '\r') {
        bufferRx += c;
      }
    }
  }

  // Seguridad local: la seta apaga las lamparas sin depender del PC
  if (setaPulsada() && valor_lamparas != 0) {
    valor_lamparas = 0;
    analogWrite(PIN_LAMPARAS, 0);
    Serial.println("[LAMPARAS] Apagadas por SETA");
  }

  // Enviar seta y referencia cuando cambien, o periodicamente
  bool periodico = (millis() - ultimo_envio_periodico) > INTERVALO_PERIODICO_MS;
  enviarSeta(periodico);
  enviarRef(periodico);
  if (periodico) ultimo_envio_periodico = millis();

  // Fin del pulso PRINT (no bloqueante)
  if (pulso_print_activo && (millis() - t_inicio_pulso >= DURACION_PULSO_PRINT_MS)) {
    digitalWrite(PIN_PRINT_PULSE, LOW);
    pulso_print_activo = false;
    Serial.println("[PULSE] Fin del pulso");
  }
}
////////////////////////////////////////////////////////////////////////////////////////////////////
bool setaPulsada() {
  if (SIMULAR_SETA_LIBERADA) return false;
  return digitalRead(PIN_SAFE) == LOW;
}

void enviarSeta(bool forzar) {
  bool pulsada = setaPulsada();
  if (pulsada != seta_anterior || forzar) {
    enviar(pulsada ? "SETA:1" : "SETA:0");
    seta_anterior = pulsada;
  }
}

void enviarRef(bool forzar) {
  bool ref = digitalRead(PIN_REF_X);
  if (ref != ref_x_anterior || forzar) {
    enviar(ref ? "REF:1" : "REF:0");
    ref_x_anterior = ref;
  }
}

void procesarLinea(String linea) {
  linea.trim();
  if (linea.length() == 0) return;

  Serial.print("RX: ");
  Serial.println(linea);

  if (linea.startsWith("LAMP:")) {
    int valor = linea.substring(5).toInt();
    if (valor < 0) valor = 0;
    if (valor > LAMPARAS_MAX) valor = LAMPARAS_MAX;
    if (setaPulsada() && valor > 0) {
      Serial.println("[LAMPARAS] Orden ignorada: seta pulsada");
      return;
    }
    valor_lamparas = valor;
    analogWrite(PIN_LAMPARAS, valor_lamparas);
    Serial.print("[LAMPARAS] Valor: ");
    Serial.println(valor_lamparas);

  } else if (linea == "PULSE") {
    if (!pulso_print_activo) {
      digitalWrite(PIN_PRINT_PULSE, HIGH);
      t_inicio_pulso = millis();
      pulso_print_activo = true;
      Serial.println("[PULSE] Iniciado");
    }
  }
}

void enviar(String msg) {
  if (cliente && cliente.connected()) {
    cliente.println(msg);   // println añade el \n
  }
}