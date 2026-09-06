import { invoke as nativeInvoke } from '@tauri-apps/api/core';
import { listen as nativeListen } from '@tauri-apps/api/event';
import { getCurrentWindow as nativeWindow } from '@tauri-apps/api/window';
let csrf: string | null = null;
export function useCompanionSession(token:string){csrf=token;}
export function isCompanion(){return csrf!==null;}
export async function invoke<T>(command:string,args?:Record<string,unknown>):Promise<T>{
 if(csrf===null)return nativeInvoke<T>(command,args);
 const response=await fetch('/api/invoke',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Jarvis-CSRF':csrf},body:JSON.stringify({command,args:args??{}})});
 const value=await response.json();if(!response.ok)throw new Error(value.error||'Private companion request failed');return value.result as T;
}
export const listen:typeof nativeListen=((...args:Parameters<typeof nativeListen>)=>csrf===null?nativeListen(...args):Promise.resolve(()=>{})) as typeof nativeListen;
export function getCurrentWindow(){return csrf===null?nativeWindow():{label:'companion'};}
