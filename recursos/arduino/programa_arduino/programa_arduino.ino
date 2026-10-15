// M-Duino: servidor TCP para la app singlepass
//   Recibe : LAMP:<0-100>   potencia de las lamparas NIR en %
//            PULSE          pulso de print go (rele R1_4, DURACION_PULSO_PRINT_MS)
//   Envia  : SETA:1 / SETA:0  (al cambiar y cada INTERVALO_PERIODICO_MS)
//            REF:1  / REF:0   (X referenciado, idem)

#include <Ethernet.h>

// ===== ENTRADAS / SALIDAS =====
#define PIN_SAFE        I1_2   // Seta: HIGH = NO pulsada, LOW = pulsada
#define PIN_REF_X       I1_4   // X referenciado (dryve D1)
#define PIN_LAMPARAS    A0_0   // Salida 0-10 V (analogWrite 0..255)
#define PIN_PRINT_PULSE R1_4   // Pulso de arranque de impresion

#define POTENCIA_MAX_PCT        100
#define PWM_MAX                 255
#define DURACION_PULSO_PRINT_MS 300
#define INTERVALO_PERIODICO_MS  1000

// ===== RED =====
byte mac[] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0x02};
IPAddress ip(192, 168, 79, 180);
#define PUERTO_TCP 5000

EthernetServer server(PUERTO_TCP);
EthernetClient cliente;          // cliente al que se envian SETA/REF
String bufferRx = "";

int  valor_lamparas = 0;         // PWM aplicado (0..255)
bool seta_anterior = false;
bool ref_x_anterior = false;
bool pulso_print_activo = false;
unsigned long t_inicio_pulso = 0;
unsigned long ultimo_envio_periodico = 0;

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

void loop() {
  // --- Atender al cliente que tenga datos, sea el actual o uno nuevo.
  //     Un cliente antiguo que murio sin cerrar ya no bloquea a los demas.
  EthernetClient con_datos = server.available();
  if (con_datos) {
    if (con_datos != cliente) {
      if (cliente && cliente.connected()) cliente.stop();   // soltar el anterior
      cliente = con_datos;
      bufferRx = "";
      Serial.println("Cliente conectado");
      enviarSeta(true);
      enviarRef(true);
    }
    while (con_datos.available()) {
      char c = con_datos.read();
      if (c == '\n') {
        procesarLinea(bufferRx);
        bufferRx = "";
      } else if (c != '\r') {
        bufferRx += c;
      }
    }
  }

  // --- Seguridad: la seta apaga las lamparas aunque nadie lo pida
  if (setaPulsada() && valor_lamparas != 0) {
    valor_lamparas = 0;
    analogWrite(PIN_LAMPARAS, 0);
    Serial.println("[LAMPARAS] Apagadas por SETA");
  }

  // --- Estado hacia la app: al cambiar y periodicamente (latido)
  bool periodico = (millis() - ultimo_envio_periodico) > INTERVALO_PERIODICO_MS;
  enviarSeta(periodico);
  enviarRef(periodico);
  if (periodico) ultimo_envio_periodico = millis();

  // --- Fin del pulso de print go
  if (pulso_print_activo && (millis() - t_inicio_pulso >= DURACION_PULSO_PRINT_MS)) {
    digitalWrite(PIN_PRINT_PULSE, LOW);
    pulso_print_activo = false;
    Serial.println("[PULSE] Fin del pulso");
  }
}

bool setaPulsada() {
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
    int potencia = linea.substring(5).toInt();          // 0..100 %
    if (potencia < 0) potencia = 0;
    if (potencia > POTENCIA_MAX_PCT) potencia = POTENCIA_MAX_PCT;
    if (setaPulsada() && potencia > 0) {
      Serial.println("[LAMPARAS] Orden ignorada: seta pulsada");
      return;
    }
    valor_lamparas = map(potencia, 0, POTENCIA_MAX_PCT, 0, PWM_MAX);
    analogWrite(PIN_LAMPARAS, valor_lamparas);
    Serial.print("[LAMPARAS] ");
    Serial.print(potencia);
    Serial.print(" % -> PWM ");
    Serial.println(valor_lamparas);

  } else if (linea == "PULSE") {
    if (setaPulsada()) {
      Serial.println("[PULSE] Ignorado: seta pulsada");
      return;
    }
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
    cliente.println(msg);   // println anade el \n
  }
}
