import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {RunRecovery} from './RunRecovery';
import type {ConversationRun} from './conversationRuns';
afterEach(cleanup);
const row={runId:'root',turnId:'old',sessionId:'owner',phase:'unresolved',context:'unknown',answer:'',progress:[],startedAt:1,route:'difficult',speak:false,seenEvents:[],lastSequence:1} as ConversationRun;
it('unknown outcome never offers report retry',()=>{
 render(<RunRecovery run={row} recover={vi.fn()} retryIncomplete={vi.fn()}/>);
 expect(screen.queryByText('Retry known incomplete report processing')).toBeNull();
 expect(screen.getByText('Continue without retrying the earlier action')).toBeTruthy();
 expect(screen.getByText(/No accepted completed result is available/)).toBeTruthy();
 expect(screen.queryByText(/provider outcome is unknown/)).toBeNull();
});
it('known incomplete retry locks double clicks and never acknowledges unknown',async()=>{
 let finish!:()=>void;const retry=vi.fn(()=>new Promise<void>(resolve=>{finish=resolve;}));const recover=vi.fn();
 render(<RunRecovery run={{...row,reportRecovery:{kind:'known-incomplete'}}} recover={recover} retryIncomplete={retry}/>);
 const button=screen.getByText('Retry known incomplete report processing');fireEvent.click(button);fireEvent.click(button);
 expect(retry).toHaveBeenCalledTimes(1);expect(recover).not.toHaveBeenCalled();finish();
 await waitFor(()=>expect((button as HTMLButtonElement).disabled).toBe(false));
});
it('canonical save pending takes precedence over new processing',()=>{
 render(<RunRecovery run={{...row,persistencePending:true,reportRecovery:{kind:'known-incomplete'}}} recover={vi.fn()} retryIncomplete={vi.fn()}/>);
 expect(screen.getByText('Retry saving this exact result')).toBeTruthy();
 expect(screen.queryByText('Retry known incomplete report processing')).toBeNull();
});

it('shows resume for a durable queued retry and failed known report',()=>{
 const {rerender}=render(<RunRecovery run={{...row,phase:'running',reportRecovery:{kind:'known-incomplete',sourceRunId:'old',newTurnId:'durable'}}} recover={vi.fn()} retryIncomplete={vi.fn()}/>);
 expect(screen.getByText('Retry known incomplete report processing')).toBeTruthy();
 rerender(<RunRecovery run={{...row,phase:'failed',reportRecovery:{kind:'known-incomplete'}}} recover={vi.fn()} retryIncomplete={vi.fn()}/>);
 expect(screen.getByText('Retry known incomplete report processing')).toBeTruthy();
});
it('labels retained response local validation without promising zero cost for remaining synthesis',async()=>{
 const retry=vi.fn(async()=>{});const recover=vi.fn();
 render(<RunRecovery run={{...row,reportRecovery:{kind:'retained-response',sourceRunId:'old',newTurnId:'saved-retry'}}} recover={recover} retryIncomplete={retry}/>);
 expect(screen.getByText(/reuses only valid source-backed work.*unsupported claims remain rejected.*Remaining extraction and final synthesis may require paid model calls/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Recover retained evidence and continue'}));
 await waitFor(()=>expect(retry).toHaveBeenCalledTimes(1));expect(recover).not.toHaveBeenCalled();
 expect(screen.queryByText('Retry known incomplete report processing')).toBeNull();
});
it('offers only new paid final composition when native diagnosis confirms completed extraction',async()=>{
 const retry=vi.fn(async()=>{});const recover=vi.fn();
 render(<RunRecovery run={{...row,reportRecovery:{kind:'final-incomplete',sourceRunId:'failed-final',newTurnId:'new-final'}}} recover={recover} retryIncomplete={retry}/>);
 expect(screen.getByText(/new paid final model request.*old failed turn is not replayed.*extraction is not repeated/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Retry final report composition'}));
 await waitFor(()=>expect(retry).toHaveBeenCalledTimes(1));expect(recover).not.toHaveBeenCalled();
 expect(screen.queryByText('Recover retained evidence and continue')).toBeNull();
});

it('received but locally rejected result retains exact continue action without asserting transport uncertainty',async()=>{
 const recover=vi.fn(async()=>{});const retry=vi.fn();
 render(<RunRecovery run={{...row,progress:['Received response rejected by local source validation']}} recover={recover} retryIncomplete={retry}/>);
 fireEvent.click(screen.getByRole('button',{name:'Continue without retrying the earlier action'}));
 await waitFor(()=>expect(recover).toHaveBeenCalledExactlyOnceWith('acknowledge-unknown'));
 expect(retry).not.toHaveBeenCalled();expect(screen.queryByText(/provider outcome is unknown/)).toBeNull();
});
