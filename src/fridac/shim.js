const _global = typeof globalThis !== 'undefined' ? globalThis : global;

if (!_global.Module) _global.Module = {};
if (!_global.Memory) _global.Memory = {};
if (!_global.Process) _global.Process = {};
if (!_global.Thread) _global.Thread = {};
if (!_global.Kernel) _global.Kernel = {};

if (typeof _global.Interceptor === 'undefined' && _global.Gum && _global.Gum.Interceptor) {
    _global.Interceptor = _global.Gum.Interceptor;
    _global.Stalker = _global.Gum.Stalker;
    _global.NativeFunction = _global.Gum.NativeFunction;
    _global.NativeCallback = _global.Gum.NativeCallback;
}

const originalModule = _global.Module;

if (typeof originalModule.findExportByName !== 'function') {
    originalModule.findExportByName = function(moduleName, exportName) {
        if (moduleName === null) {
            return originalModule.findGlobalExportByName(exportName);
        }
        try {
            const mod = Process.getModuleByName(moduleName);
            return mod ? mod.findExportByName(exportName) : null;
        } catch (e) {
            return null;
        }
    };
}

if (typeof originalModule.getExportByName !== 'function') {
    originalModule.getExportByName = function(moduleName, exportName) {
        if (moduleName === null) {
            return originalModule.getGlobalExportByName(exportName);
        }
        try {
            const mod = Process.getModuleByName(moduleName);
            return mod ? mod.getExportByName(exportName) : null;
        } catch (e) {
            return null;
        }
    };
}

if (typeof originalModule.findSymbolByName !== 'function') {
    originalModule.findSymbolByName = function(moduleName, symbolName) {
        if (moduleName === null) {
            return originalModule.findGlobalExportByName(symbolName);
        }
        try {
            const mod = Process.getModuleByName(moduleName);
            return mod ? mod.findSymbolByName(moduleName) : null;
        } catch (e) {
            return null;
        }
    };
}

if (typeof originalModule.getSymbolByName !== 'function') {
    originalModule.getSymbolByName = function(moduleName, symbolName) {
        if (moduleName === null) {
            return originalModule.getGlobalExportByName(symbolName);
        }
        try {
            const mod = Process.getModuleByName(moduleName);
            return mod ? mod.getSymbolByName(symbolName) : null;
        } catch (e) {
            return null;
        }
    };
}

if (typeof originalModule.getBaseAddress !== 'function') {
    originalModule.getBaseAddress = function(moduleName) {
        try {
            return Process.getModuleByName(moduleName).base;
        } catch (e) {
            return null;
        }
    };
}

if (typeof originalModule.findBaseAddress !== 'function') {
    originalModule.findBaseAddress = function(moduleName) {
        try {
            return Process.getModuleByName(moduleName).base;
        } catch (e) {
            return null;
        }
    };
}

if (typeof originalModule.ensureInitialized !== 'function') {
    originalModule.ensureInitialized = function(moduleName) {
        try {
            Process.getModuleByName(moduleName).ensureInitialized();
        } catch (e) {

        }
    };
}

const originalMemory = _global.Memory;

const memoryReadMethods = [
    'readPointer',
    'readByteArray',
    'readUtf8String',
    'readUtf16String',
    'readS8',
    'readU8',
    'readS16',
    'readU16',
    'readS32',
    'readU32',
    'readFloat',
    'readDouble',
    'readS64',
    'readU64',
    'readShort',
    'readUShort',
    'readInt',
    'readUInt',
    'readLong',
    'readULong',
    'readCString',
    'readAnsiString',
]

memoryReadMethods.forEach(function(methodName) {
    if (typeof originalMemory[methodName] !== 'function') {
        originalMemory[methodName] = function(targetPtr, ...args) {
            const ptrObj = (targetPtr instanceof NativePointer) ? targetPtr : ptr(targetPtr);
            return ptrObj[methodName](...args);
        };
    }
});

const memoryWriteMethods = [
    'writePointer',
    'writeByteArray',
    'writeUtf8String',
    'writeUtf16String',
    'writeS8',
    'writeU8',
    'writeS16',
    'writeU16',
    'writeS32',
    'writeU32',
    'writeFloat',
    'writeDouble',
    'writeS64',
    'writeU64',
    'writeShort',
    'writeUShort',
    'writeInt',
    'writeUInt',
    'writeLong',
    'writeULong',
    'writeCString',
    'writeAnsiString',
]

memoryWriteMethods.forEach(function(methodName) {
    if (typeof originalMemory[methodName] !== 'function') {
        originalMemory[methodName] = function(targetPtr, value, ...args) {
            const ptrObj = (targetPtr instanceof NativePointer) ? targetPtr : ptr(targetPtr);
            ptrObj[methodName](value, ...args);
            return ptrObj;
        };
    }
});

if (typeof originalMemory.scanSync !== 'function' && typeof originalMemory.scan === 'function') {
    originalMemory.scanSync = function(address, size, pattern) {
        return originalMemory.scan(address, size, pattern);
    }
}

const namespaceOverrides = {
    Process: {},
    Kernel: {},
};

function buildEnumerationOverride(namespaceStr, methodName) {
    const originalNamespace = _global[namespaceStr];
    if (!originalNamespace[methodName]) return;

    const originalMethod = originalNamespace[methodName];
    if (!originalMethod) return;

    const syncName = methodName + 'Sync';
    namespaceOverrides[namespaceStr][syncName] = function(...args) {
        return originalMethod.apply(originalNamespace, args);
    }

    namespaceOverrides[namespaceStr][methodName] = function(...args) {
        const lastArg = args[args.length - 1];

        if (lastArg && typeof lastArg === 'object' && typeof lastArg.onMatch === 'function') {
            const nativeArgs = args.slice(0, args.length - 1);
            const results = originalMethod.apply(originalNamespace, nativeArgs);

            for (let i = 0; i < results.length; i++) {
                const directive = lastArg.onMatch(results[i]);
                if (directive === 'stop') break;
            }
            if (typeof lastArg.onComplete === 'function') lastArg.onComplete();
            return;
        } else {
            return originalMethod.apply(originalNamespace, args);
        }
    }
}

buildEnumerationOverride('Process', 'enumerateModules');
buildEnumerationOverride('Process', 'enumerateThreads');
buildEnumerationOverride('Process', 'enumerateRanges');
buildEnumerationOverride('Kernel', 'enumerateModules');
buildEnumerationOverride('Kernel', 'enumerateModuleRanges');

['Process', 'Kernel'].forEach(function(ns) {
    const original = _global[ns];
    if (!original) return;

    const overrides = namespaceOverrides[ns];

    const proxyObj = new Proxy({}, {
        get(target, prop) {
            if (overrides.hasOwnProperty(prop)) return overrides[prop];
            const value = original[prop];
            if (typeof value === 'function') return value.bind(original);
            return value;
        },
        set(target, prop, value) {
            try {
                original[prop] = value;
            } catch (e) {

            }
            return true;
        },
        has(target, prop) {
            return prop in overrides || prop in original;
        },
    });

    try {
        _global[ns] = proxyObj;
    } catch (e) {
        Object.defineProperty(_global, ns, { value: proxyObj, writable: true, configurable: true });
    }
});

if (typeof originalModule.enumerateExports !== 'function') {
    originalModule.enumerateExports = function(moduleName, callbacks) {
        let mod;
        try {
            mod = Process.getModuleByName(moduleName);
        } catch (e) {
            return callbacks ? undefined : [];
        }

        const results = mod.enumerateExports();
        if (callbacks && typeof callbacks.onMatch === 'function') {
            for (let i = 0; i < results.length; i++) {
                if (callbacks.onMatch(results[i]) === 'stop') break;
                if (typeof callbacks.oncomplete === 'function') callbacks.oncomplete();
            }
        } else {
            return results;
        }
    };
}

if (typeof originalModule.enumerateImports !== 'function') {
    originalModule.enumerateImports = function(moduleName, callbacks) {
        let mod;
        try {
            mod = Process.getModuleByName(moduleName);
        } catch (e) {
            return callbacks ? undefined : [];
        }

        const results = mod.enumerateImports();
        if (callbacks && typeof callbacks.onMatch === 'function') {
            for (let i = 0; i < results.length; i++) {
                if (callbacks.onMatch(results[i]) === 'stop') break;
                if (typeof callbacks.oncomplete === 'function') callbacks.oncomplete();
            }
        } else {
            return results;
        }
    };
}

if (typeof originalModule.enumerateSymbols !== 'function') {
    originalModule.enumerateSymbols = function(moduleName, callbacks) {
        let mod;
        try {
            mod = Process.getModuleByName(moduleName);
        } catch (e) {
            return callbacks ? undefined : [];
        }

        const results = mod.enumerateSymbols();
        if (callbacks && typeof callbacks.onMatch === 'function') {
            for (let i = 0; i < results.length; i++) {
                if (callbacks.onMatch(results[i]) === 'stop') break;
                if (typeof callbacks.oncomplete === 'function') callbacks.oncomplete();
            }
        } else {
            return results;
        }
    };
}
