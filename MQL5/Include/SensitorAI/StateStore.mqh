//+------------------------------------------------------------------+
//| StateStore.mqh - local persistence (second line of defence).      |
//| The primary source of truth is always MT5 itself (orders,         |
//| positions, history). This file remembers which setup ids were     |
//| already sent and the initial risk of each position, so that a     |
//| restart never re-sends an order nor loses the 1R reference.       |
//| Format: Common\Files\SensitorAI\<tag>_state.csv, key,value lines  |
//+------------------------------------------------------------------+
#ifndef SENSITOR_STATESTORE_MQH
#define SENSITOR_STATESTORE_MQH

class CStateStore
  {
private:
   string            m_path;
   string            m_keys[];
   string            m_vals[];

   int               Find(const string key) const
     {
      for(int i=0;i<ArraySize(m_keys);i++) if(m_keys[i]==key) return i;
      return -1;
     }

public:
   bool              Init(const string tag)
     {
      m_path="SensitorAI\\"+tag+"_state.csv";
      FolderCreate("SensitorAI",FILE_COMMON);
      return Load();
     }

   bool              Load(void)
     {
      ArrayResize(m_keys,0); ArrayResize(m_vals,0);
      if(!FileIsExist(m_path,FILE_COMMON)) return true;
      int h=FileOpen(m_path,FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ);
      if(h==INVALID_HANDLE) return false;
      while(!FileIsEnding(h))
        {
         string line=FileReadString(h);
         int p=StringFind(line,",");
         if(p<=0) continue;
         Set(StringSubstr(line,0,p),StringSubstr(line,p+1),false);
        }
      FileClose(h);
      return true;
     }

   bool              Save(void)
     {
      string tmp=m_path+".tmp";
      int h=FileOpen(tmp,FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
      if(h==INVALID_HANDLE) return false;
      for(int i=0;i<ArraySize(m_keys);i++) FileWriteString(h,m_keys[i]+","+m_vals[i]+"\n");
      FileClose(h);
      // atomic-ish replace
      if(FileIsExist(m_path,FILE_COMMON)) FileDelete(m_path,FILE_COMMON);
      return FileMove(tmp,FILE_COMMON,m_path,FILE_COMMON|FILE_REWRITE);
     }

   void              Set(const string key,const string val,const bool save=true)
     {
      int i=Find(key);
      if(i<0) { i=ArraySize(m_keys); ArrayResize(m_keys,i+1); ArrayResize(m_vals,i+1); m_keys[i]=key; }
      m_vals[i]=val;
      if(save) Save();
     }

   bool              Has(const string key) const { return Find(key)>=0; }
   string            Get(const string key,const string def="") const { int i=Find(key); return i<0 ? def : m_vals[i]; }
   double            GetD(const string key,const double def=0.0) const { int i=Find(key); return i<0 ? def : StringToDouble(m_vals[i]); }

   void              Remove(const string key)
     {
      int i=Find(key);
      if(i<0) return;
      int n=ArraySize(m_keys);
      for(int j=i+1;j<n;j++) { m_keys[j-1]=m_keys[j]; m_vals[j-1]=m_vals[j]; }
      ArrayResize(m_keys,n-1); ArrayResize(m_vals,n-1);
      Save();
     }
  };

#endif
