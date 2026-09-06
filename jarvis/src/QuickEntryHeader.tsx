import {useState} from 'react';
import {invoke} from './transport';
export function QuickEntryHeader({title,context}:{title:string;context:string}){
 const [error,setError]=useState('');
 return <><div className="hud-title"><span className="orb"/><strong title={title} style={{overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',flex:1,minWidth:0}}>{title}</strong><small>{context}</small><button type="button" className="quiet" aria-label="Close Quick Entry without cancelling requests" onClick={()=>{void invoke('quick_entry_control',{visible:false}).catch(error=>setError(String(error)));}}>Close</button></div>{error&&<small role="alert">Could not close Quick Entry: {error}</small>}</>;
}
