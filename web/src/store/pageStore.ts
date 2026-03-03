import { defineStore } from "pinia";
import * as cookie from "@/utils/cookie"
import axios, { CancelTokenSource } from "axios";
import api from "@/utils/api";

// Configure axios default settings
axios.defaults.timeout = 10000; // 10 second timeout (reduce wait time)

interface ChatMessageItem{
    author: string,
    text: string,
    date?: string,
    generate:boolean,
    markdownText?:string, 
    prevText?:string,
    finalText?:string, 
    type?:string,
    index?:number, 
    status?:string|undefined, 
    steps?: any, 
}
interface SessionItem{
    id: string;
    title: string;
    select: boolean;
    edit: boolean;
    chat_info: ChatMessageItem[];
    execute_info: ChatMessageItem[];
    analysis_info: ChatMessageItem[];
}
interface DocItem{
    content: string,
    metadata: {
        page:number,
        source: string
    }
}
interface DocCompute{
    [key:string]: string[]
}
interface AnalysisFile{
    id: number;
    filename: string;
    absolute_path: string;
    description: string;
    metadata: any;
}

interface StateInterface{
    
    token:string;
    
    sessions: SessionItem[];
    current_session: SessionItem;
    
    cancelTokenSource: CancelTokenSource|undefined;
    
    headimg: string;
    
    settings: {
        show: boolean,
        api_key: string,
        base_url: string,
        executor: boolean,
        docs: DocItem[],
        docCompute: DocCompute,
        tools:string[]
    },
    
    analysis_files: {
        show: boolean,
        files: AnalysisFile[],
        selects: number[]
    },
    execute_files: {
        show: boolean,
        files: AnalysisFile[],
        selects: number[]
    },
    
    // Initialization state
    _initialized: boolean,
    _initPromise: Promise<void> | null
}

export default defineStore("page",{
    state:():StateInterface=>{
        return {
            token: cookie.getLogin(),
            sessions: [],
            current_session: {} as SessionItem,
            cancelTokenSource: undefined,
            headimg: new URL("../assets/avatar.jpg", import.meta.url).href,
            settings: {
                show: false,
                api_key: "",
                base_url: "",
                executor: false,
                docs: [],
                docCompute: {},
                tools:[]
            },
            analysis_files: {
                show: false,
                files: [],
                selects: []
            },
            execute_files: {
                show: false,
                files: [],
                selects: []
            },
            
            // Initialization state
            _initialized: false,
            _initPromise: null
        }
    },
    actions:{
        
        async init(){
            // Prevent duplicate initialization
            if (this._initialized) {
                return;
            }
            if (this._initPromise) {
                return this._initPromise;
            }
            
            this._initPromise = this._doInit();
            return this._initPromise;
        },
        
        async _doInit() {
            // Create request with timeout - 3 seconds, fail fast
            const timeout = 3000;
            const createTimeoutPromise = () => new Promise((_, reject) => 
                setTimeout(() => reject(new Error('Request timeout')), timeout)
            );
            
            // Try to read cache from sessionStorage (available on page refresh)
            const cachedSessions = sessionStorage.getItem('cached_sessions');
            const cachedSettings = sessionStorage.getItem('cached_settings');
            const cacheTime = sessionStorage.getItem('cache_time');
            const isCacheValid = cacheTime && (Date.now() - parseInt(cacheTime)) < 60000; // Cache valid within 1 minute
            
            // If valid cache exists, use cached data for fast render first
            if (isCacheValid && cachedSessions) {
                try {
                    const ids = JSON.parse(cachedSessions);
                    this.sessions = ids.map((item: any) => ({
                        id: item.id,
                        title: item.title,
                        select: false,
                        edit: false,
                        chat_info: [],
                        execute_info: [],
                        analysis_info: []
                    }));
                    if (this.sessions.length) {
                        this.current_session = this.sessions[0];
                        this.current_session.select = true;
                    }
                    if (cachedSettings) {
                        const settings = JSON.parse(cachedSettings);
                        this.settings.api_key = settings.api_key ?? this.settings.api_key;
                        this.settings.base_url = settings.base_url ?? this.settings.base_url;
                        this.settings.executor = settings.executor ?? false;
                    }
                } catch (e) {
                    // Cache parse failed, ignore
                }
            }
            
            // Parallel requests for sessions and settings (background refresh)
            const [sessionsResult, settingsResult] = await Promise.allSettled([
                Promise.race([axios.get(api.get_all_ids), createTimeoutPromise()]),
                Promise.race([axios.get(api.get_initial_settings), createTimeoutPromise()])
            ]);
            
            // Process sessions result
            if (sessionsResult.status === 'fulfilled') {
                const sessions = sessionsResult.value as any;
                const ids = sessions.data?.sessions ?? [];
                // Update cache
                sessionStorage.setItem('cached_sessions', JSON.stringify(ids));
                sessionStorage.setItem('cache_time', Date.now().toString());
                
                this.sessions = ids.map((item: any) => ({
                    id: item.id,
                    title: item.title,
                    select: false,
                    edit: false,
                    chat_info: [],
                    execute_info: [],
                    analysis_info: []
                }));
                if (this.sessions.length) {
                    this.current_session = this.sessions[0];
                    this.current_session.select = true;
                } else {
                    this.setDefaultSession();
                }
            } else if (!isCacheValid || !cachedSessions) {
                // No cache and request failed
                this.setDefaultSession();
            }
            
            // Process settings result
            if (settingsResult.status === 'fulfilled') {
                const initial_settings = settingsResult.value as any;
                // Update cache
                sessionStorage.setItem('cached_settings', JSON.stringify(initial_settings.data));
                
                this.settings.api_key = initial_settings.data?.['api_key'] ?? this.settings.api_key;
                this.settings.base_url = initial_settings.data?.["base_url"] ?? this.settings.base_url;
                this.settings.executor = initial_settings.data?.["executor"] ?? false;
            }
            
            this._initialized = true;
        },
        
        setDefaultSession(){
            this.current_session = {
                id: "000",
                title: "000",
                select: false,
                edit: false,
                chat_info: [],
                execute_info: [],
                analysis_info: []
            }
           
        },
        
        getCurrentSession() {
            return this.current_session;
        },
        
        setCurrentSession(sessionId: string) {
            const session = this.sessions.find(s => s.id == sessionId);
            if (session) {
                this.sessions.forEach(s => (s.select = false));
                session.select = true;
                this.current_session = session;
            }
            // this.sessions.forEach(s=>s.edit=false);
        },
        async deleteSession(id:string){
            const url = api.delete_session.replace("id", id.toString().padStart(3, "0"));
            const result = await axios({
                method: "POST",
                url
            })
            return result.data;
        },
        async createSession(title:string="New Session"){
            const result = await axios({
                method: "POST",
                url: api.create_session,
                data:{
                    title
                }
            })
            return result.data;
        },
        
        updateSessions(id:string, title:string="New Session"){
            
            if(this.sessions.find(s=>s.id==id)){
                let index = this.sessions.indexOf(this.getCurrentSession());
                this.sessions = this.sessions.filter(s=>s.id != id);
                if(this.sessions.length==0){
                    
                    this.setDefaultSession();
                    return;
                }
                if(index>=this.sessions.length){
                    index -= 1;
                }
                this.setCurrentSession(this.sessions[index].id);
            }
            
            else{
                this.sessions.unshift({
                    id,
                    title,
                    select: false,
                    edit: false,
                    chat_info: [],
                    execute_info: [],
                    analysis_info: []
                })
            }
        },
        async updateSessionTitle(id:string, title:string){
            this.sessions.forEach(session=>{
                if(session.id == id){
                    session.title = title;
                }
            })
            const url = api.update_session_title.replace("id", id.toString().padStart(3, "0"));
            const result = await axios({
                method: "POST",
                url: url,
                data:{
                    title
                }
            })
            return result.data;
        },
        
        async getCurrentChatInfo(){
            const id = this.getCurrentSession().id;
            
            if(!id) return true;
            
            if(!this.sessions.length) return true;
            const result = await axios.get(`${api.get_chat_info}${id.toString().padStart(3, "0")}/`)
            const history = result.data['history'] ?? []
            if(history){
                const historys:ChatMessageItem[] = [];
                for (let i = 0; i < history.length; i++) {
                    historys.push({
                        author: "user",
                        text: history[i]['asking'],
                        generate: false
                    })
                    
                    // Check status - only processing status shows thinking
                    // interrupted and error status show respective messages
                    const status = history[i]['status'];
                    const response = history[i]['response'];
                    
                    let displayText = response;
                    let isGenerating = false;
                    
                    if (status === 'processing' && (!response || response === '')) {
                        // Processing - Chat Agent does not show stop button
                        displayText = "thinking...";
                        isGenerating = false;  // Chat Agent does not need stop button
                    } else if (status === 'interrupted') {
                        // Interrupted - show interrupt message or keep original response
                        displayText = response || "Request was interrupted";
                    } else if (status === 'error') {
                        // Error - show error message
                        displayText = response || "An error occurred";
                    }
                    
                    historys.push({
                        author: "computer",
                        text: displayText,
                        generate: isGenerating
                    })
                }
                this.current_session.chat_info = historys;
            }
            return true;
        },
        async addCurrentChatInfo(author:string, text:string, generate:boolean){
            this.current_session.chat_info.push({
                author,
                text,
                generate
            })
            return true
        },
        async receiveMessageFromServer(text:string, callback:Function){
            try {
                if (!this.current_session || !this.current_session.id) {
                    if(callback) callback("Error: No session available")
                    return;
                }
                
                this.cancelTokenSource = axios.CancelToken.source();
                const result = await axios({
                    method: "POST",
                    url: api.run_chat,
                    cancelToken: this.cancelTokenSource.token, 
                    data: {
                        id: this.current_session.id.toString().padStart(3, "0"),
                        dataPath: [],
                        targetDialog: text
                    }
                })
                if(callback) callback(result.data['interpretation'] ?? "No Result")
            } catch (error: any) {
                if (axios.isCancel(error)) {
                    if(callback) callback(error.message)
                } else {
                    if(callback) callback("Error: " + (error.message || "Unknown error"))
                }
            }
        },
        async updateCurrentChatInfo(text:string, generate:boolean){
            const info_length = this.current_session.chat_info.length;
            
            if(this.current_session.chat_info[info_length-1].text=="thinking..."){
                this.current_session.chat_info[info_length-1].text = text;
            }
            this.current_session.chat_info[info_length-1].generate = generate;
        },
        async stopCurrentChatInfo(){
            // First cancel current axios request
            this.cancelTokenSource?.cancel("User Cancels");
            
            if (!this.current_session?.id) {
                console.warn("No session to stop");
                return false;
            }
            
            const taskId = this.current_session.id.toString().padStart(3, "0");
            
            try {
                const result = await axios({
                    method: "POST",
                    url: api.stop_task,
                    data: { 
                        id: taskId,
                        agent_type: 'chat',
                        force: false
                    },
                    timeout: 5000
                });
                console.log(`Chat task ${taskId} stop request sent:`, result.data);
                return true;
            } catch (error) {
                console.error(`Error stopping chat task ${taskId}:`, error);
                return true;  // Return true even on failure to indicate stop was attempted
            }
        },
        
       async getExecuteFiles(){
            const result = await axios(api.get_execute_files);
            this.execute_files.files = result.data.files;
        },
        async updateExecuteFileDescription(id:number, filename:string, description:string){
            try {
                const result = await axios({
                    method: "POST",
                    url: api.update_execute_file_description,
                    data:{
                        id,
                        filename,
                        description
                    }
                });
                if(result.data['status']=='success'){
                    this.execute_files.files.forEach(fileInfo=>{
                        if(fileInfo.id==id){
                            fileInfo.description = description;
                        }
                    })
                }
            } catch (error) { /* Ignore error */ }
        },
        
        async getCurrentExecuteInfo(){
            const id = this.getCurrentSession().id;
            
            if(!id) return true;
            
            if(!this.sessions.length) return true;
            const url = api.get_execute_info.replace("id", id.toString().padStart(3, "0"));
            try {
                // Set shorter timeout
                const result = await axios.get(`${url}`, { timeout: 5000 });
                
                if(result.data['status']=="success"){
                    const history = result.data['history'] ?? []
                    if(history){
                        const historys:ChatMessageItem[] = [];
                        for (let i = 0; i < history.length; i++) {
                            
                            if(history[i]['asking']){
                                historys.push({
                                    author: "user",
                                    text: history[i]['asking'],
                                    generate: false,
                                    type: "text",
                                    status: undefined
                                })
                                
                                if(history[i]['plan'] && history[i]['plan']["plan"] && history[i]['plan']["plan"].length > 0){
                                    const markdown_arr = [];
                                    markdown_arr.push("### PLAN")
                                    const plans = history[i]['plan']["plan"];
                                    const steps = [];
                                    for (let i = 0; i < plans.length; i++) {
                                        const step = [];
                                        step.push(`#### Step ${plans[i]['step_number']}:`)
                                        step.push(`#### Description:`);
                                        step.push(plans[i]['description']);
                                        if(plans[i].hasOwnProperty("input_filename")){
                                            step.push(`#### Input Files:`);
                                            for (let m = 0; m < plans[i]["input_filename"].length; m++) {
                                                step.push(`* ${plans[i]["input_filename"][m]}`);
                                            }
                                        }
                                        if(plans[i].hasOwnProperty("output_filename")){
                                            step.push(`#### Output Files:`);
                                            for (let m = 0; m < plans[i]["output_filename"].length; m++) {
                                                step.push(`* ${plans[i]["output_filename"][m]}`);
                                            }
                                        }
                                        step.push(`#### Tools:`);
                                        step.push(plans[i]['tools']);
                                        steps.push(step.join("\n"));
                                    }
                                    historys.push({
                                        author: "computer",
                                        text: "### PLAN\n"+steps.join("___\n"),
                                        generate: false,
                                        prevText: JSON.stringify(history[i]['plan'], null, 4),
                                        type: "plan",
                                        status: undefined
                                    })
                                }
                            }
                            else{

                            }
                        }
                        this.current_session.execute_info = historys;
                        
                        // Check if plan data already exists
                        var hasPlanData = historys.some((info: any) => info.type === "plan");
                    } else {
                        this.current_session.execute_info = [];
                        var hasPlanData = false;
                    }
                    if(result.data.hasOwnProperty("execute_agent")){
                        const execute_agent = result.data.execute_agent;
                        
                        if(execute_agent.stage == "PLAN" && execute_agent.status != "thinking"){
                            // PLAN stage, non-thinking state
                            // If plan data exists, history already contains PLAN message, no need to add
                            // Frontend will show Execute Plan button based on type "plan" in history
                        }
                        else if(execute_agent.stage == "PLAN" && execute_agent.status == "thinking"){
                            // PLAN stage, thinking state
                            if(!hasPlanData) {
                                // If no plan data, only show thinking animation
                                const hasThinkingMessage = this.current_session.execute_info.some(
                                    (info: any) => info.type === "thinking" || info.text.includes("thinking...")
                                );
                                if(!hasThinkingMessage) {
                                    this.current_session.execute_info.push({
                                        author: "computer",
                                        text: "thinking...",
                                        generate: true,
                                        type: "thinking",
                                        status: execute_agent.status
                                    });
                                }
                            } else {
                                // If plan data exists but status is thinking, don't add extra PLAN message
                                // History already contains PLAN data, just add EXECUTE progress bar
                                const percent = execute_agent.step_completion;
                                const hasExecuteMessage = this.current_session.execute_info.some(
                                    (info: any) => info.text.includes("##### EXECUTE")
                                );
                                if(!hasExecuteMessage) {
                                    this.current_session.execute_info.push({
                                        author: "computer",
                                        text: `##### EXECUTE ${percent}`,
                                        generate: true,
                                        type: "execute",
                                        status: execute_agent.status
                                    });
                                }
                            }
                        }
                        else if(execute_agent.stage == "EXECUTE" || execute_agent.stage == "DEBUG"){
                            const percent = execute_agent.step_completion;
                            this.current_session.execute_info.push({
                                author: "computer",
                                text: `##### EXECUTE ${percent}`,
                                generate: true,
                                type: "execute",
                                status: execute_agent.status
                            })
                        }
                        
                        else if(execute_agent.stage == "PAUSED" || execute_agent.stage == "ERROR"){
                            const percent = execute_agent.step_completion;
                            const markdown_arr = [];
                            if(execute_agent.stage == "PAUSED") markdown_arr.push(`##### Stopped By User ${percent}`);
                            else markdown_arr.push(`##### Execute Error ${percent}`);

                            const history = result.data['history'] ?? [];
                            let temp_steps: any[] = [];
                            
                            // Find entries with step data in history (search from end)
                            if(history.length){
                                for(let h = history.length - 1; h >= 0; h--){
                                    const historyEntry = history[h];
                                    if(historyEntry.hasOwnProperty("execute") && 
                                       historyEntry.execute.hasOwnProperty("steps") &&
                                       historyEntry.execute.steps.length > 0){
                                        // Found entry with step data
                                        const steps = historyEntry.execute.steps;
                                        temp_steps = steps;
                                        for (let i = 0; i < steps.length; i++) {
                                            if(steps[i].hasOwnProperty("shell") && steps[i].hasOwnProperty("step_number")){
                                                markdown_arr.push('``` \n'+steps[i].shell+'```')
                                            }
                                        }
                                        break; // Exit loop after found
                                    }
                                }
                            }

                            this.current_session.execute_info.push({
                                author: "computer",
                                text: markdown_arr.join("\n"),
                                generate: false,
                                type: execute_agent.stage == "PAUSED" ? "paused" : "error",
                                status: execute_agent.status,
                                steps: temp_steps,
                            })
                        }
                        
                        else if(execute_agent.stage == "FINISH"){
                            const history = result.data['history'] ?? [];
                            let foundSteps = false;
                            
                            // Find entries with step data in history (search from end)
                            if(history.length){
                                for(let h = history.length - 1; h >= 0 && !foundSteps; h--){
                                    const historyEntry = history[h];
                                    if(historyEntry.hasOwnProperty("execute") && 
                                       historyEntry.execute.hasOwnProperty("steps") &&
                                       historyEntry.execute.steps.length > 0){
                                        const steps = historyEntry.execute.steps;
                                        const markdown_arr = [];
                                        markdown_arr.push("### Current Steps")
                                        for (let i = 0; i < steps.length; i++) {
                                            if(steps[i].hasOwnProperty("shell")){
                                                markdown_arr.push('``` \n'+steps[i].shell+'```')
                                            }
                                        }
                                        this.current_session.execute_info.push({
                                            author: "computer",
                                            text: markdown_arr.join("\n"),
                                            generate: false,
                                            type: "finish",
                                            status: execute_agent.status,
                                            steps: steps
                                        })
                                        foundSteps = true;
                                    }
                                }
                                
                                // Check report (use last entry)
                                const end_history = history.slice(-1)[0];
                                if(end_history.hasOwnProperty("report")){
                                    // Check report status
                                    const isGenerating = end_history.report_status === "generating";
                                    const reportText = isGenerating ? "Generate Report..." : end_history.report;
                                    
                                    this.current_session.execute_info.push({
                                        author: "computer",
                                        text: reportText,
                                        generate: isGenerating,
                                        type: isGenerating ? "thinking" : "text",
                                        status: execute_agent.status
                                    })
                                }
                                // If no report field but report_status is generating, also show generating state
                                else if(end_history.hasOwnProperty("report_status") && end_history.report_status === "generating"){
                                    this.current_session.execute_info.push({
                                        author: "computer",
                                        text: "Generate Report...",
                                        generate: true,
                                        type: "thinking",
                                        status: execute_agent.status
                                    })
                                }
                            }
                        }
                    }
                }
            } catch (error) { /* Ignore error */ }
            finally{
                return true;
            }
        },
        async stopCurrentExecuteInfo(){
            // First cancel current axios request
            this.cancelTokenSource?.cancel("User Cancels");
            
            if (!this.current_session?.id) {
                console.warn("No session to stop");
                return false;
            }
            
            const taskId = this.current_session.id.toString().padStart(3, "0");
            
            try {
                const result = await axios({
                    method: "POST",
                    url: api.stop_task,
                    data: { 
                        id: taskId,
                        agent_type: 'chat',
                        force: false
                    },
                    timeout: 5000  // 5 second timeout
                });
                console.log(`Task ${taskId} stop request sent:`, result.data);
                return true;
            } catch (error) {
                console.error(`Error stopping task ${taskId}:`, error);
                // Return true even if API fails to indicate stop was attempted
                return true;
            }
        },
        async stopCurrentExecutePlan(force: boolean = false){
            if (!this.current_session?.id) {
                console.warn("No session to stop");
                return false;
            }
            
            const taskId = this.current_session.id.toString().padStart(3, "0");
            
            try {
                const result = await axios({
                    method: "POST",
                    url: api.stop_plan,
                    data: { 
                        id: taskId,
                        force: force
                    },
                    timeout: 5000  // 5 second timeout
                });
                console.log(`Plan ${taskId} stop request sent:`, result.data);
                return true;
            } catch (error) {
                console.error(`Error stopping plan ${taskId}:`, error);
                // Return true even if API fails to indicate stop was attempted
                return true;
            }
        },
        async addCurrentExecuteInfo(author:string, text:string, generate:boolean, type:string="text"){
            this.current_session.execute_info.push({
                author,
                text,
                generate,
                type
            })
            return true
        },
        async updateCurrentExecuteInfo(text:string, generate:boolean){
            const info_length = this.current_session.execute_info.length;
            
            if(this.current_session.execute_info[info_length-1].text=="thinking..."){
                this.current_session.execute_info[info_length-1].text = text;
            }
            this.current_session.execute_info[info_length-1].generate = generate;
        },
        async receiveExecuteMessageFromServer(text:string, dataPath:string[],callback:Function){
            try {
                if (!this.current_session || !this.current_session.id) {
                    if(callback) callback("Error: No session available")
                    return;
                }
                
                this.cancelTokenSource = axios.CancelToken.source();
                const result = await axios({
                    method: "POST",
                    url: api.run_plan,
                    cancelToken: this.cancelTokenSource.token, 
                    data: {
                        id: this.current_session.id.toString().padStart(3, "0"),
                        dataPath: dataPath,
                        targetDialog: text
                    }
                })
                if(callback) callback(result.data['interpretation'] ?? "No Result")
            } catch (error: any) {
                if (axios.isCancel(error)) {
                    if(callback) callback(error.message)
                } else {
                    if(callback) callback("Error: " + (error.message || "Unknown error"))
                }
            }
        },
        async updateCurrentPlan(plan:any){
            if (!this.current_session?.id) return false;
            
            const result = await axios({
                method: "POST",
                url: api.update_plan,
                headers: {
                    'Content-Type': 'application/json'
                },
                data:{
                    id: this.current_session.id.toString().padStart(3, "0"),
                    plan
                }
            });
            return true;
        },
        async executePlan(){
            if (!this.current_session?.id) return false;
            
            await axios({
                method: "POST",
                url: api.execute_plan,
                headers: { 'Content-Type': 'application/json' },
                data:{
                    id: this.current_session.id.toString().padStart(3, "0"),
                    datalist: []
                }
            });
            return true;
        },
        async updateCurrentExecuteStep(stepNumber:number, content:string){
            if (!this.current_session?.id) return false;
            
            await axios({
                method: "POST",
                url: api.update_step,
                headers: { 'Content-Type': 'application/json' },
                data:{
                    id: this.current_session.id.toString().padStart(3, "0"),
                    stepNumber,
                    content,
                }
            });
            return true;
        },
        async generateReport(){
            if (!this.current_session || !this.current_session.id) {
                return false;
            }
            const url = api.generate_report.replace("id", this.current_session.id.toString().padStart(3, "0"));
            await axios.get(url);
            return true;
        },
        
        async getAnalysisFiles(){
            const result = await axios(api.get_analysis_files);
            this.analysis_files.files = result.data.files;
        },
        async updateAnalysisFileDescription(id:number, filename:string, description:string){
            try {
                const result = await axios({
                    method: "POST",
                    url: api.update_analysis_file_description,
                    data:{
                        id,
                        filename,
                        description
                    }
                });
                if(result.data['status']=='success'){
                    this.analysis_files.files.forEach(fileInfo=>{
                        if(fileInfo.id==id){
                            fileInfo.description = description;
                        }
                    })
                }
            } catch (error) { /* Ignore error */ }
        },
        
        async getCurrentAnalysisInfo(){
            const id = this.getCurrentSession().id;
            
            if(!id) return true;
            
            if(!this.sessions.length) return true;
            const url = api.get_analysis_info.replace("id", id.toString().padStart(3, "0"));
            try {
                const result = await axios.get(`${url}`)
                if(result.data['status']=="success"){
                    const history = result.data['history'] ?? []
                    if(history){
                        const historys:ChatMessageItem[] = [];
                        for (let i = 0; i < history.length; i++) {
                            historys.push({
                                author: "user",
                                text: history[i]['asking'],
                                generate: false
                            })
                            
                            // Check status - only processing status shows thinking
                            const status = history[i]['status'];
                            const response = history[i]['response'];
                            
                            let displayText = response;
                            let isGenerating = false;
                            
                            if (status === 'processing' && (!response || response === '')) {
                                // Processing - Analysis Agent also does not need stop button
                                displayText = "thinking...";
                                isGenerating = false;
                            } else if (status === 'interrupted') {
                                displayText = response || "Request was interrupted";
                            } else if (status === 'error') {
                                displayText = response || "An error occurred";
                            }
                            
                            historys.push({
                                author: "computer",
                                text: displayText,
                                generate: isGenerating
                            })
                        }
                        this.current_session.analysis_info = historys;
                    }
                }
            } catch (error) {
                
            }
            finally{
                return true;
            }
        },
        async addCurrentAnalysisInfo(author:string, text:string, generate:boolean){
            this.current_session.analysis_info.push({
                author,
                text,
                generate
            })
            return true
        },
        async updateCurrentAnalysisInfo(text:string, generate:boolean){
            const info_length = this.current_session.analysis_info.length;
            
            if(this.current_session.analysis_info[info_length-1].text=="thinking..."){
                this.current_session.analysis_info[info_length-1].text = text;
            }
            this.current_session.analysis_info[info_length-1].generate = generate;
        },
        async receiveAnalysisMessageFromServer(text:string, dataPath:string[],callback:Function){
            try {
                this.cancelTokenSource = axios.CancelToken.source();
                const result = await axios({
                    method: "POST",
                    url: api.run_analysis,
                    cancelToken: this.cancelTokenSource.token, 
                    data: {
                        
                        id: this.current_session.id.toString().padStart(3, "0"),
                        dataPath: dataPath,
                        targetDialog: text
                    }
                })
                if(callback) callback(result.data['interpretation'] ?? "No Result")
            } catch (error) {
                
                if (axios.isCancel(error)) {
                    if(callback) callback(error.message)
                }
                else{
                    if(callback) callback("Error")
                }
            }
        },
        async stopCurrentAnalysisInfo(){
            // First cancel current axios request
            this.cancelTokenSource?.cancel("User Cancels");
            
            if (!this.current_session?.id) {
                console.warn("No session to stop");
                return false;
            }
            
            const taskId = this.current_session.id.toString().padStart(3, "0");
            
            try {
                const result = await axios({
                    method: "POST",
                    url: api.stop_task,
                    data: { 
                        id: taskId,
                        agent_type: 'analysis',
                        force: false
                    },
                    timeout: 5000
                });
                console.log(`Analysis task ${taskId} stop request sent:`, result.data);
                return true;
            } catch (error) {
                console.error(`Error stopping analysis task ${taskId}:`, error);
                return true;  // Return true even on failure
            }
        },
          
        async updateSettings(){
            const result = await axios({
                method: "POST",
                url: api.update_settings,
                data:{
                    api_key:this.settings.api_key,
                    base_url: this.settings.base_url,
                    executor: this.settings.executor
                }
            })
            return result.data;
        },
        
        async getDocFiles(){
            if(this.settings.docs.length==0){
                // Try to read from cache
                const cachedDocs = sessionStorage.getItem('cached_docs');
                if (cachedDocs) {
                    try {
                        this.settings.docs = JSON.parse(cachedDocs);
                        this.computeDoc();
                    } catch (e) { /* Ignore */ }
                }
                
                // Background request for update
                try {
                const result = await axios.get(api.get_doc_files);
                this.settings.docs = result.data["files"]??[];
                    sessionStorage.setItem('cached_docs', JSON.stringify(this.settings.docs));
                this.computeDoc();
                    } catch (e) { /* Ignore */ }
            }
        },
        async addDocFile(pageContent:any){
            if(pageContent.page!=-1 && pageContent.content!=""){
                this.settings.docs.push({
                    content: pageContent.content,
                    metadata:{
                        page: pageContent.page,
                        source: "tools"
                    }
                })
                this.computeDoc();
                const result = await axios({
                    method: "POST",
                    url: api.update_doc_files,
                    data:this.settings.docCompute
                })
                return result.data;
            }else{
                return false;
            }
        },
        async deleteDocFile(pageContent:any){
            if(pageContent.page!=-1 && pageContent.content!=""){
                this.settings.docs = this.settings.docs.filter(doc=> doc.content!=pageContent.content);
                this.computeDoc();
                const result = await axios({
                    method: "POST",
                    url: api.update_doc_files,
                    data:this.settings.docCompute
                })
                return result.data;
            }else{
                return false;
            }
        },
        computeDoc(){
            // Support both page and phase fields, use category or default if neither exists
            const getPageKey = (doc: DocItem): string | number => {
                const meta = doc.metadata as any;
                if (meta.page !== undefined && meta.page !== null) {
                    return meta.page;
                }
                if (meta.phase !== undefined && meta.phase !== null) {
                    return `Phase ${meta.phase}`;
                }
                if (meta.category) {
                    return meta.category;
                }
                return 'Uncategorized';
            };
            
            let pages = [...new Set(this.settings.docs.map(doc => getPageKey(doc)))];
            // Sort pages: numbers first, then strings
            pages = pages.sort((a, b) => {
                const aIsNum = typeof a === 'number' || !isNaN(Number(a));
                const bIsNum = typeof b === 'number' || !isNaN(Number(b));
                if (aIsNum && bIsNum) {
                    return Number(a) - Number(b);
                }
                if (aIsNum) return -1;
                if (bIsNum) return 1;
                return String(a).localeCompare(String(b));
            });
            
            const computes: DocCompute = {};
            for (let i = 0; i < pages.length; i++) {
                const pageKey = pages[i];
                const temp_docs = this.settings.docs.filter(doc => getPageKey(doc) === pageKey);
                computes[String(pageKey)] = temp_docs.map(doc => doc.content);
            }
            this.settings.docCompute = computes;
        },
        async getToolFiles(refresh:boolean=false){
            if(this.settings.tools.length==0 || refresh){
                // Try to read from cache (when not forcing refresh)
                if (!refresh) {
                    const cachedTools = sessionStorage.getItem('cached_tools');
                    if (cachedTools) {
                        try {
                            this.settings.tools = JSON.parse(cachedTools);
                        } catch (e) { /* Ignore */ }
                    }
                }
                
                // Request latest data
                try {
                const result = await axios.get(api.get_tools_files);
                this.settings.tools = result.data["files"]??[];
                    sessionStorage.setItem('cached_tools', JSON.stringify(this.settings.tools));
                    } catch (e) { /* Ignore */ }
            }
        },
        async addKnowledgeEntry(content: string, source: string = 'custom'){
            const result = await axios({
                method: "POST",
                url: api.upload_tool_file,
                data: {
                    content: content,
                    source: source
                }
            });
            return result.data;
        },
        async deleteToolFile(itemId: string){
            if(itemId){
                const result = await axios({
                    method: "POST",
                    url: api.delete_tool_file,
                    data:{
                        id: itemId
                    }
                });
                // Remove from local state
                this.settings.tools = (this.settings.tools as any[]).filter(
                    (item: any) => item.id !== itemId
                );
                return result.data?.status === 'success';
            }
            else{
                return false;
            }
        },
        async uploadToGoogleDrive(link:string){
            if(link){
                const result = await axios({
                    method: "POST",
                    url: api.upload_file_from_google_drive,
                    data:{
                        id: this.current_session.id,
                        link: link
                    }
                })
                return result.data;
            }else{
                return false;
            }
        }
    }
})