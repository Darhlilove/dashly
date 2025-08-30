/**
 * Custom hook for session storage caching of query results
 */
import { useState, useEffect, useCallback } from "react";
import { ExecuteResponse } from "../types";

interface CacheEntry {
  data: ExecuteResponse;
  timestamp: number;
  query: string;
  sql: string;
}

const CACHE_KEY = "dashly_query_cache";
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

export function useSessionCache() {
  const [cache, setCache] = useState<Map<string, CacheEntry>>(new Map());

  // Load cache from session storage on mount
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(CACHE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        const cacheMap = new Map<string, CacheEntry>();

        // Filter out expired entries
        const now = Date.now();
        Object.entries(parsed).forEach(([key, entry]) => {
          const cacheEntry = entry as CacheEntry;
          if (now - cacheEntry.timestamp < CACHE_DURATION) {
            cacheMap.set(key, cacheEntry);
          }
        });

        setCache(cacheMap);
      }
    } catch (error) {
      console.warn("Failed to load query cache from session storage:", error);
    }
  }, []);

  // Save cache to session storage whenever it changes
  useEffect(() => {
    try {
      const cacheObject = Object.fromEntries(cache);
      sessionStorage.setItem(CACHE_KEY, JSON.stringify(cacheObject));
    } catch (error) {
      console.warn("Failed to save query cache to session storage:", error);
    }
  }, [cache]);

  const getCacheKey = useCallback((sql: string, query: string): string => {
    return `${sql.trim()}_${query.trim()}`;
  }, []);

  const getCachedResult = useCallback(
    (sql: string, query: string): ExecuteResponse | null => {
      const key = getCacheKey(sql, query);
      const entry = cache.get(key);

      if (!entry) return null;

      // Check if entry is still valid
      const now = Date.now();
      if (now - entry.timestamp > CACHE_DURATION) {
        // Remove expired entry
        setCache((prev) => {
          const newCache = new Map(prev);
          newCache.delete(key);
          return newCache;
        });
        return null;
      }

      return entry.data;
    },
    [cache, getCacheKey]
  );

  const setCachedResult = useCallback(
    (sql: string, query: string, data: ExecuteResponse) => {
      const key = getCacheKey(sql, query);
      const entry: CacheEntry = {
        data,
        timestamp: Date.now(),
        query,
        sql,
      };

      setCache((prev) => {
        const newCache = new Map(prev);
        newCache.set(key, entry);

        // Limit cache size to prevent memory issues
        if (newCache.size > 50) {
          // Remove oldest entries
          const entries = Array.from(newCache.entries());
          entries.sort((a, b) => a[1].timestamp - b[1].timestamp);

          // Keep only the 40 most recent entries
          const toKeep = entries.slice(-40);
          return new Map(toKeep);
        }

        return newCache;
      });
    },
    [getCacheKey]
  );

  const clearCache = useCallback(() => {
    setCache(new Map());
    try {
      sessionStorage.removeItem(CACHE_KEY);
    } catch (error) {
      console.warn("Failed to clear query cache from session storage:", error);
    }
  }, []);

  const getCacheStats = useCallback(() => {
    return {
      size: cache.size,
      entries: Array.from(cache.values()).map((entry) => ({
        query: entry.query,
        timestamp: entry.timestamp,
        age: Date.now() - entry.timestamp,
      })),
    };
  }, [cache]);

  return {
    getCachedResult,
    setCachedResult,
    clearCache,
    getCacheStats,
  };
}
