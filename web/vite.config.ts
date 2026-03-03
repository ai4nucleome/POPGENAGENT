import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path';

// @ts-ignore
export default defineConfig(({ command, mode })=>{
    loadEnv(mode, process.cwd());
    const isDev = mode === 'development';
    
    return {
        plugins: [vue()],
        
        // Build optimization
        build: {
            outDir: 'dist',
            minify: 'terser',
            terserOptions: {
                compress: {
                    drop_console: true,
                    drop_debugger: true,
                    pure_funcs: ['console.log', 'console.info'],
                },
            },
            rollupOptions: {
                output: {
                    // Finer-grained code splitting
                    manualChunks(id) {
                        if (id.includes('node_modules')) {
                            // Vue core
                            if (id.includes('vue') || id.includes('vue-router') || id.includes('pinia')) {
                                return 'vue-vendor';
                            }
                            // UI library
                            if (id.includes('naive-ui')) {
                                return 'naive-ui';
                            }
                            // Markdown related
                            if (id.includes('markdown-it') || id.includes('highlight.js') || id.includes('katex')) {
                                return 'markdown';
                            }
                            // Utility libraries
                            if (id.includes('axios') || id.includes('lodash')) {
                                return 'utils';
                            }
                            // Icon library
                            if (id.includes('@iconify')) {
                                return 'icons';
                            }
                            // Other dependencies
                            return 'vendor';
                        }
                    },
                    // Asset file naming
                    chunkFileNames: 'js/[name]-[hash].js',
                    entryFileNames: 'js/[name]-[hash].js',
                    assetFileNames: (assetInfo) => {
                        const info = assetInfo.name?.split('.');
                        const ext = info?.[info.length - 1];
                        if (/\.(png|jpe?g|gif|svg|webp|ico)$/i.test(assetInfo.name || '')) {
                            return 'img/[name]-[hash][extname]';
                        }
                        if (/\.(woff2?|eot|ttf|otf)$/i.test(assetInfo.name || '')) {
                            return 'fonts/[name]-[hash][extname]';
                        }
                        if (/\.css$/i.test(assetInfo.name || '')) {
                            return 'css/[name]-[hash][extname]';
                        }
                        return 'assets/[name]-[hash][extname]';
                    }
                }
            },
            chunkSizeWarningLimit: 1000,
            // Enable CSS code splitting
            cssCodeSplit: true,
            // Generate source map (disabled in production)
            sourcemap: isDev,
            // Enable gzip compressed size report
            reportCompressedSize: false,
        },
        
        base: './',
        
        resolve: {
            alias: {
                '@': path.resolve('./src')
            }
        },
        
        server: {
            fs: {
                allow: ['..']
            },
            // Dev server optimization
            warmup: {
                clientFiles: [
                    './src/main.ts',
                    './src/App.vue',
                    './src/views/popgenagent/Index.vue',
                    './src/views/home/Index.vue'
                ]
            }
        },
        
        // Dependency pre-bundling optimization
        optimizeDeps: {
            include: [
                'vue',
                'vue-router',
                'pinia',
                'axios',
                'naive-ui',
                'markdown-it',
                'highlight.js',
                '@iconify/vue'
            ],
            // Force pre-bundling
            force: false
        },
        
        // CSS optimization
        css: {
            devSourcemap: isDev,
        },
        
        define: {
            __DEV_MODE__: isDev
        },
        
        // Dev server performance
        esbuild: {
            // Remove console in production
            drop: isDev ? [] : ['console', 'debugger'],
        }
    }
});
