(function(){
  const PREFIX='zhao-radar:v1:';
  const parse=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key))??fallback}catch{return fallback}};
  window.RadarStore={
    getPreferences(defaults){return {...defaults,...parse(PREFIX+'preferences',{})}},
    savePreferences(value){localStorage.setItem(PREFIX+'preferences',JSON.stringify(value))},
    getJobState(id){const modern=parse(PREFIX+'job:'+id,null);if(modern)return modern;const legacy=parse('jobstate:'+id,{});if(Object.keys(legacy).length)localStorage.setItem(PREFIX+'job:'+id,JSON.stringify(legacy));return legacy},
    saveJobState(id,patch){const next={...this.getJobState(id),...patch};localStorage.setItem(PREFIX+'job:'+id,JSON.stringify(next));return next},
    clearPreferences(){localStorage.removeItem(PREFIX+'preferences')}
  };
})();
