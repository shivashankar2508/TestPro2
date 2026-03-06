const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const TerserPlugin = require('terser-webpack-plugin');

const isDevelopment = process.env.NODE_ENV !== 'production';

module.exports = {
    entry: './src/index.js',
    output: {
        path: path.resolve(__dirname, 'dist'),
        filename: 'bundle.[contenthash].js',
        clean: true,
        publicPath: '/',
    },
    mode: isDevelopment ? 'development' : 'production',
    devtool: isDevelopment ? 'source-map' : false,
    module: {
        rules: [
            {
                test: /\.js$/,
                exclude: /node_modules/,
                use: {
                    loader: 'babel-loader',
                    options: {
                        presets: ['@babel/preset-env'],
                    },
                },
            },
            {
                test: /\.css$/,
                use: ['style-loader', 'css-loader'],
            },
        ],
    },
    optimization: {
        minimize: !isDevelopment,
        minimizer: [
            new TerserPlugin({
                terserOptions: {
                    compress: {
                        drop_console: !isDevelopment,
                    },
                    output: {
                        comments: false,
                    },
                },
                extractComments: false,
            }),
        ],
        splitChunks: {
            chunks: 'all',
            cacheGroups: {
                vendors: {
                    test: /[\\/]node_modules[\\/]/,
                    name: 'vendors',
                    priority: 10,
                },
                common: {
                    minChunks: 2,
                    priority: 5,
                    reuseExistingChunk: true,
                },
            },
        },
    },
    plugins: [
        new HtmlWebpackPlugin({
            template: './public/index.html',
            filename: 'index.html',
            minify: isDevelopment ? false : {
                removeComments: true,
                collapseWhitespace: true,
                removeRedundantAttributes: true,
                useShortDoctype: true,
                removeEmptyAttributes: true,
                removeStyleLinkTypeAttributes: true,
                keepClosingSlash: true,
                minifyJS: true,
                minifyCSS: true,
                minifyURLs: true,
            },
        }),
    ],
    devServer: isDevelopment ? {
        static: {
            directory: path.join(__dirname, 'public'),
        },
        historyApiFallback: {
            rewrites: [
                { from: /^\/$/, to: '/landing.html' },
                { from: /^\/login$/, to: '/auth/login.html' },
                { from: /^\/register$/, to: '/auth/register.html' },
                { from: /^\/dashboard$/, to: '/dashboard.html' },
                { from: /^\/admin$/, to: '/admin.html' },
            ],
        },
        compress: true,
        port: 3000,
        hot: true,
        open: false,
        client: {
            overlay: {
                errors: true,
                warnings: false,
            },
        },
        proxy: {
            '/api': {
                target: 'http://localhost:8001',
                pathRewrite: { '^/api': '' },
                changeOrigin: true,
            },
        },
    } : undefined,
};

