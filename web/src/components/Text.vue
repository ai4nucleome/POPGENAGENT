<template>
    <div class="text-slate-800" :class="wrapClass">
        <div ref="textRef" class="leading-relaxed break-words">
            <!-- AI reply message -->
            <div v-if="!inversion">
                <div v-if="generate && text === 'thinking...'" class="flex items-center gap-3 py-1">
                    <div class="typing-dots flex gap-1">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                    <span class="text-slate-400 text-sm">Thinking...</span>
                </div>
                <div v-else class="markdown-body" :class="{ 'markdown-body-generate': generate }" v-html="text" />
            </div>
            <!-- User message -->
            <div v-else class="whitespace-pre-wrap" v-text="text" />
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import MarkdownIt from 'markdown-it'
import mdKatex from '@traptitech/markdown-it-katex'
import mila from 'markdown-it-link-attributes'
import hljs from 'highlight.js'
import "katex/dist/katex.min.css"
import "@/styles/github-markdown.less"
import "@/styles/highlight.less"

// Backend API URL
const API_BASE_URL = "http://localhost:8000"

const textRef = ref<HTMLElement>()
const props = defineProps({
    text: {
        type: String,
        default: ""
    },
    inversion: {
        type: Boolean,
        default: false
    },
    asRawText: {
        type: Boolean,
        default: false
    },
    generate: {
        type: Boolean,
        default: false
    }
})

const mdi = new MarkdownIt({
    html: false,
    linkify: true,
    highlight(code, language) {
        const validLang = !!(language && hljs.getLanguage(language))
        if (validLang) {
            const lang = language ?? ''
            return highlightBlock(hljs.highlight(code, { language: lang }).value, lang)
        }
        return highlightBlock(hljs.highlightAuto(code).value, '')
    },
})

mdi.use(mila, { attrs: { target: '_blank', rel: 'noopener' } })
mdi.use(mdKatex, { blockClass: 'katexmath-block rounded-md p-[10px]', errorColor: ' #cc0000' })

// Custom image render rule - convert /output/ path to API URL
const defaultImageRender = mdi.renderer.rules.image || function(tokens: any, idx: any, options: any, env: any, self: any) {
    return self.renderToken(tokens, idx, options)
}

mdi.renderer.rules.image = function(tokens: any, idx: any, options: any, env: any, self: any) {
    const token = tokens[idx]
    const srcIndex = token.attrIndex('src')
    
    if (srcIndex >= 0) {
        let src = token.attrs[srcIndex][1]
        // If path starts with /output/ or ./output/, convert to API URL
        if (src.startsWith('/output/')) {
            token.attrs[srcIndex][1] = `${API_BASE_URL}/api${src}`
        } else if (src.startsWith('./output/')) {
            token.attrs[srcIndex][1] = `${API_BASE_URL}/api/output/${src.slice(9)}`
        }
    }
    
    // Add style class
    token.attrPush(['class', 'report-image'])
    token.attrPush(['loading', 'lazy'])
    
    return defaultImageRender(tokens, idx, options, env, self)
}

const wrapClass = computed(() => {
    return [
        'text-wrap',
        'min-w-[20px]',
        'px-4 py-3',
        props.inversion 
            ? 'rounded-2xl rounded-tr-md bg-gradient-to-br from-primary-500 to-accent-500 shadow-md shadow-primary-500/20' 
            : 'rounded-2xl rounded-tl-md bg-white shadow-soft border border-slate-100',
        props.inversion ? 'text-white' : 'text-slate-800',
        props.inversion ? 'message-request' : 'message-reply',
    ]
})

const preprocessMath = (input: string) => {
  return input
    .replace(/\\begin{equation}/g, '$$')
    .replace(/\\end{equation}/g, '$$');
};

const text = computed(() => {
    const value = preprocessMath(props.text ?? '');
    if (!props.asRawText)
        return mdi.render(value)
    return value;
})

function highlightBlock(str: string, lang?: string) {
    return `<pre class="code-block-wrapper">
                <div class="code-block-header">
                    <span class="code-block-header__lang">${lang}</span>
                    <button class="code-block-header__copy" onclick="navigator.clipboard.writeText(this.parentElement.nextElementSibling.textContent)">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                        </svg>
                    </button>
                </div>
                <code class="hljs code-block-body ${lang}">${str}</code>
            </pre>`
}
</script>

<style lang="scss">
/* Typing animation */
.typing-dots {
    span {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: linear-gradient(135deg, #3b7ffb, #8a52fc);
        animation: typing-bounce 1.4s ease-in-out infinite;
        
        &:nth-child(1) { animation-delay: -0.32s; }
        &:nth-child(2) { animation-delay: -0.16s; }
        &:nth-child(3) { animation-delay: 0s; }
    }
}

@keyframes typing-bounce {
    0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
    40% { transform: scale(1.2); opacity: 1; }
}

/* Markdown style */
.markdown-body {
    background-color: transparent;
    font-size: 14px;
    line-height: 1.7;

    p {
        white-space: pre-wrap;
        margin-bottom: 12px;
        
        &:last-child {
            margin-bottom: 0;
        }
    }

    ol {
        list-style-type: decimal;
        padding-left: 1.5em;
        margin: 12px 0;
    }

    ul {
        list-style-type: disc;
        padding-left: 1.5em;
        margin: 12px 0;
    }
    
    li {
        margin: 4px 0;
    }
    
    code {
        background-color: #f1f5f9;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 13px;
        font-family: 'JetBrains Mono', monospace;
        color: #e11d48;
    }
    
    pre code,
    pre tt {
        line-height: 1.65;
        background: transparent;
        padding: 0;
        color: inherit;
    }

    .highlight pre,
    pre {
        background-color: #0f172a;
        border-radius: 12px;
        overflow: hidden;
        margin: 12px 0;
    }

    code.hljs {
        padding: 16px;
        display: block;
        overflow-x: auto;
    }

    .code-block {
        &-wrapper {
            position: relative;
            background: #0f172a;
            border-radius: 12px;
            overflow: hidden;
        }

        &-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 16px;
            background: #1e293b;
            border-bottom: 1px solid #334155;
            
            &__lang {
                font-size: 12px;
                color: #94a3b8;
                font-family: 'JetBrains Mono', monospace;
                text-transform: uppercase;
            }
            
            &__copy {
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 4px;
                border-radius: 6px;
                color: #94a3b8;
                cursor: pointer;
                transition: all 0.2s;
                background: transparent;
                border: none;

                &:hover {
                    color: #f8fafc;
                    background: #334155;
                }
            }
        }
        
        &-body {
            margin: 0 !important;
        }
    }
    
    /* Table style */
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 16px 0;
        border-radius: 8px;
        overflow: hidden;
    }
    
    th, td {
        border: 1px solid #e2e8f0;
        padding: 10px 14px;
        text-align: left;
    }
    
    th {
        background: #f8fafc;
        font-weight: 600;
    }
    
    tr:nth-child(even) {
        background: #f8fafc;
    }
    
    /* Report image style */
    img.report-image {
        max-width: 100%;
        height: auto;
        border-radius: 12px;
        margin: 16px 0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        border: 1px solid #e2e8f0;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        cursor: pointer;
        
        &:hover {
            transform: scale(1.02);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
        }
    }

    /* Cursor animation while generating */
    &.markdown-body-generate > dd:last-child:after,
    &.markdown-body-generate > dl:last-child:after,
    &.markdown-body-generate > dt:last-child:after,
    &.markdown-body-generate > h1:last-child:after,
    &.markdown-body-generate > h2:last-child:after,
    &.markdown-body-generate > h3:last-child:after,
    &.markdown-body-generate > h4:last-child:after,
    &.markdown-body-generate > h5:last-child:after,
    &.markdown-body-generate > h6:last-child:after,
    &.markdown-body-generate > li:last-child:after,
    &.markdown-body-generate > ol:last-child li:last-child:after,
    &.markdown-body-generate > p:last-child:after,
    &.markdown-body-generate > pre:last-child code:after,
    &.markdown-body-generate > td:last-child:after,
    &.markdown-body-generate > ul:last-child li:last-child:after {
        animation: blink 1s steps(5, start) infinite;
        content: '▋';
        font-weight: 400;
        margin-left: 2px;
        vertical-align: baseline;
        color: #3b7ffb;
    }

    @keyframes blink {
        to {
            visibility: hidden;
        }
    }
}
</style>
