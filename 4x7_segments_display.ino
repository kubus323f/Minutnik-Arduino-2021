void setup(){
  Serial.begin(9600);
  for(int i = 2; i < 14; i++)
  {
    pinMode(i, OUTPUT);
  }
  pinMode(16, INPUT_PULLUP); //RESET
  pinMode(19, OUTPUT);
  pinMode(15, INPUT_PULLUP); //SPEED
  pinMode(14, INPUT_PULLUP); //PAUSA
  pinMode(A5, INPUT_PULLUP); //MODE
  Serial.println("Uruchomiono tryb MIN:SEC.");
}
int last = 0;
byte a = 0;
byte b = 0;
int c = 0;
byte d = 0;
int Delay = 1000; //maks 32000
byte last18PinState = 0;
byte last14PinState = 0;
byte last15PinState = 0;
byte last16PinState = 0;
byte Mode = 2;
byte Sec = 0;
bool Dwukropek;
bool NotStopped = true;
int MillisPausa;
void loop(){
  digitalWrite(19, HIGH);
  if(millis() % 1000 == 0)
  {
    digitalWrite(19, LOW);
  } else{
    digitalWrite(19, HIGH);
  }
  if(digitalRead(18) == LOW && last18PinState != digitalRead(18)) //MODE
  {
    last18PinState = digitalRead(18);
    setMillis(0);
    if(Mode < 2)
      Mode++;
    else
      Mode =  0;
    last = 0;
    a = 0;
    b = 0;
    c = 0;
    d = 0;
    Sec = 0;
    switch(Mode)
    {
      case 0:
        Serial.println("Uruchomiono tryb MIN:SEC.");
        Dwukropek = true;
        break;
      case 1:
        Serial.println("Uruchomiono tryb HOUR:MIN.");
        Dwukropek = true;
        break;
      case 2:
        Serial.println("Uruchomiono tryb odliczania.");
        Dwukropek = false;
        break;
    }
  } 
  else if(last18PinState != digitalRead(18))
  {
    last18PinState = digitalRead(18);
  }
  
  if(digitalRead(14) == LOW && last14PinState != digitalRead(14)) //PAUSA
  {
    last14PinState = digitalRead(14);
    if(NotStopped)
    {
      NotStopped = false;
      Serial.println("Zatrzymano odliczanie.");
      MillisPausa = millis();
    } else{
      NotStopped = true;
      setMillis(MillisPausa);
      Serial.println("Wznowionie odliczanie.");
    }
  } 
  else if(last14PinState != digitalRead(14))
  {
    last14PinState = digitalRead(14);
  }

  if(digitalRead(15) == LOW && last15PinState != digitalRead(15)) //SPEED
  {
    last15PinState = digitalRead(15);
    if(Delay == 1000)
    {
      Delay = 500;
    } else if(Delay == 500)
    {
      Delay = 100;
    } else if(Delay == 100)
    {
      Delay = 50;
      
    } else if(Delay == 50)
    {
      Delay = 1000;
    }
    float a = Delay;
    Serial.println("Ustawiono prędkość odliczania na " + String(1000 / a) + "x");
  } 
  else if(last15PinState != digitalRead(15))
  {
    last15PinState = digitalRead(15);
  }

  if(digitalRead(16) == LOW && last16PinState != digitalRead(16)) //RESET
  {
    last16PinState = digitalRead(16);
    last = 0;
    a = 0;
    b = 0;
    c = 0;
    d = 0;
    Sec = 0;
    Delay = 1000;
    NotStopped = true;
    MillisPausa = 0;
    Mode = 0;
    Serial.println("Zresetowano Timer.");
    Serial.println("Uruchomiono tryb MIN:SEC.");
    Dwukropek = true;
    setMillis(0);
  } 
  else if(last16PinState != digitalRead(16))
  {
    last16PinState = digitalRead(16);
  }
  
  if(Dwukropek)
    dwukropek();
  WriteAt(d, 1);
  WriteAt(c, 2);
  WriteAt(b, 3);
  WriteAt(a, 4);
  if(NotStopped)
  {
    if(last + Delay <= millis())
    {
      switch(Mode)
      {
       case 0:
         Sec++;
         if(Sec % 2 == 0)
           Dwukropek = true;
         else
            Dwukropek = false;
         MinsecTimer();
         break;
       case 1:
          Sec++;
         last = millis();
         if(Sec % 2 == 0)
           Dwukropek = true;
         else
           Dwukropek = false;
         if(Sec >= 60)
         {
           hourTimer();
           Sec = 0;
         }
         break;
       case 2:
         licz();
         break;
    }
    } else if(millis() >= 30000)
    {
      setMillis(0);
      last = 0;
      //last -= Delay;
    }
  }
}
extern volatile unsigned long timer0_millis;
unsigned long new_value = 0;
void setMillis(unsigned long new_millis)
{
  uint8_t oldSREG = SREG;
  cli();
  timer0_millis = new_millis;
  SREG = oldSREG;
}
void MinsecTimer()
{
    last = millis();
    a++;
    if(a > 9)
     {
        a = 0;
        b++;
     }
     if(b > 5)
     {
        a = 0;
        b = 0;
        c++;
     } 
     if(c > 9)
     {
      a = 0;
      b = 0;
      c = 0;
      d++;
     }
     if(d > 9)
     {
      d = 0;
      c = 0;
      b = 0;
      a = 0;
     }
}
void hourTimer()
{
    a++;
    if(a > 9)
     {
        a = 0;
        b++;
     }
     if(b > 5)
     {
        a = 0;
        b = 0;
        c++;
     } 
     if(c > 9 && d < 2)
     {
      a = 0;
      b = 0;
      c = 0;
      d++;
     } else if(c > 4 && d == 2)
     {
      a = 0;
      b = 0;
      c = 0;
      d = 0;
     }
}
void licz()
{
     last = millis();
     a++;
    if(a > 9)
     {
        a = 0;
        b++;
     }
     if(b > 9)
     {
        a = 0;
        b = 0;
        c++;
     } if(c > 9)
     {
      a = 0;
      b = 0;
      c = 0;
      d++;
     }
      if(d >= 10){
        a = 0;
        b = 0;
        c = 0;
        d = 0;
    }
}

void dwukropek()
{
digitalWrite(10, LOW);
digitalWrite(11, LOW);
digitalWrite(12, LOW);
digitalWrite(13, LOW);

digitalWrite(2, LOW);
//digitalWrite(3, LOW);
digitalWrite(4, LOW);
digitalWrite(5, HIGH);
//digitalWrite(6, LOW);
//digitalWrite(7, LOW);
//digitalWrite(8, LOW);
digitalWrite(9, HIGH);
Refresh();
}

void Refresh()
{
    digitalWrite(2, HIGH);
    digitalWrite(3, HIGH);
    digitalWrite(4, HIGH);
    digitalWrite(5, HIGH);
    digitalWrite(6, HIGH);
    digitalWrite(7, HIGH);
    digitalWrite(8, HIGH);
    digitalWrite(9, LOW);
    digitalWrite(13, LOW);
    digitalWrite(10, LOW);
    digitalWrite(11, LOW);
    digitalWrite(12, LOW);
}

void WriteAt(int Liczba, int Gdzie)
{
  Refresh();
  switch(Gdzie)
  {
    case 1:
    digitalWrite(10, HIGH);
    digitalWrite(11, LOW);
    digitalWrite(12, LOW);
    digitalWrite(13, LOW);
    break;
    case 2:
    digitalWrite(10, LOW);
    digitalWrite(11, HIGH);
    digitalWrite(12, LOW);
    digitalWrite(13, LOW);
    break;
    case 3:
    digitalWrite(10, LOW);
    digitalWrite(11, LOW);
    digitalWrite(12, HIGH);
    digitalWrite(13, LOW);
    break;
    case 4:
    digitalWrite(10, LOW);
    digitalWrite(11, LOW);
    digitalWrite(12, LOW);
    digitalWrite(13, HIGH);
    break;
  }
  switch(Liczba)
  {
    case 0:
      digitalWrite(2, LOW);
      digitalWrite(3, HIGH);
      digitalWrite(4, LOW);
      digitalWrite(5, LOW);
      digitalWrite(6, LOW);
      //
      digitalWrite(7, LOW);
      digitalWrite(8, LOW);
    break;
    case 1:
      digitalWrite(2, LOW);
      digitalWrite(3, HIGH);
      digitalWrite(4, HIGH);
      digitalWrite(5, LOW);
      digitalWrite(6, HIGH);
      //
      digitalWrite(7, HIGH);
      digitalWrite(8, HIGH);
    break;
    case 2:
      digitalWrite(2, LOW);
      digitalWrite(3, LOW);
      digitalWrite(4, LOW);
      digitalWrite(5, HIGH);
      digitalWrite(6, HIGH);
      //
      digitalWrite(7, LOW);
      digitalWrite(8, LOW);
    break;
    case 3:
      digitalWrite(2, LOW);
      digitalWrite(3, LOW);
      digitalWrite(4, LOW);
      digitalWrite(5, LOW);
      digitalWrite(6, HIGH);
      //
      digitalWrite(7, LOW);
      digitalWrite(8, HIGH);
    break;
    case 4:
      digitalWrite(2, LOW);
      digitalWrite(3, LOW);
      digitalWrite(4, HIGH);
      digitalWrite(5, LOW);
      digitalWrite(6, LOW);
      //
      digitalWrite(7, HIGH);
      digitalWrite(8, HIGH);
    break;
    case 5:
      digitalWrite(2, HIGH);
      digitalWrite(3, LOW);
      digitalWrite(4, LOW);
      digitalWrite(5, LOW);
      digitalWrite(6, LOW);
      //
      digitalWrite(7, LOW);
      digitalWrite(8, HIGH);
    break;
    case 6:
      digitalWrite(2, HIGH);
      digitalWrite(3, LOW);
      digitalWrite(4, LOW);
      digitalWrite(5, LOW);
      digitalWrite(6, LOW);
      //
      digitalWrite(7, LOW);
      digitalWrite(8, LOW);
    break;
     case 7:
      digitalWrite(2, LOW);
      digitalWrite(3, HIGH);
      digitalWrite(4, LOW);
      digitalWrite(5, LOW);
      digitalWrite(6, HIGH);
      //
      digitalWrite(7, HIGH);
      digitalWrite(8, HIGH);
    break;
    case 8:
      digitalWrite(2, LOW);
      digitalWrite(3, LOW);
      digitalWrite(4, LOW);
      digitalWrite(5, LOW);
      digitalWrite(6, LOW);
      digitalWrite(7, LOW);
      digitalWrite(8, LOW);
    break;
    case 9:
      digitalWrite(2, LOW);
      digitalWrite(3, LOW);
      digitalWrite(4, LOW);
      digitalWrite(5, LOW);
      digitalWrite(6, LOW);
      digitalWrite(7, LOW);
      digitalWrite(8, HIGH);
    break;
  }
}
