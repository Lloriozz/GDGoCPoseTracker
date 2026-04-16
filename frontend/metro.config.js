// Learn more: https://docs.expo.dev/guides/customizing-metro
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// Allow Metro to bundle TFJS model weight files (.bin)
// Without this, require('../assets/models/.../.bin') would fail
config.resolver.assetExts.push('bin');

module.exports = config;
