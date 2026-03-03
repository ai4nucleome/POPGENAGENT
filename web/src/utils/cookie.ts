export function setCookie(name:string,value:any):void
{
    var Days = 365;
    var exp = new Date();
    exp.setTime(exp.getTime() + Days*24*60*60*1000);
    document.cookie = name + "="+ escape (value) + ";expires=" + exp.toUTCString();
}

export  function getCookie(name:string):string
{
    var arr,reg=new RegExp("(^| )"+name+"=([^;]*)(;|$)");
 
    if(arr=document.cookie.match(reg))
        return unescape(arr[2]);
    else
        return "";
}

export  function delCookie(name:string):void
{
    var exp = new Date();
    exp.setTime(exp.getTime() - 1);
    var cval=getCookie(name);
    if(cval!=null)
        document.cookie= name + "="+cval+";expires="+exp.toUTCString();
}

let cookieID:string = "pop_gen_agent_1";
export function getLogin():string
{
    return getCookie(cookieID);
}
export function setLogin(openid:string):void{
    setCookie(cookieID, openid);
}
export function clearLogin(){
    delCookie(cookieID);
}