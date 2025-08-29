// Session storage cache utilities for query results and dashboard data

import { ExecuteResponse } from "../types/api";
import { Dashboard } from "../types/dashboard";

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number; // Time to live in milliseconds
}

interface QueryCacheEntry extends CacheEntry<ExecuteResponse> {
  sql: string;
  question: string;
}

class SessionCache {
  private readonly QUERY_CACHE_KEY = "dashly_query_cache";
  private readonly DASHBOARD_CACHE_KEY = "dashly_dashboard_cache";
  private readonly DEFAULT_TTL = 30 * 60 * 1000; // 30 minutes
  private readonly MAX_CACHE_ENTRIES = 10;

  /**
   * Cache a query result with SQL and question for context
   */
  cacheQueryResult(
    sql: string,
    question: string,
    result: ExecuteResponse,
    ttl: number = this.DEFAULT_TTL
  ): void {
    try {
      const cache = this.getQueryCache();
      const cacheKey = this.generateQueryKey(sql, question);

      const entry: QueryCacheEntry = {
        data: result,
        sql,
        question,
        timestamp: Date.now(),
        ttl,
      };

      cache[cacheKey] = entry;

      // Limit cache size by removing oldest entries
      const entries = Object.entries(cache);
      if (entries.length > this.MAX_CACHE_ENTRIES) {
        const sortedEntries = entries.sort(
          ([, a], [, b]) => a.timestamp - b.timestamp
        );
        const entriesToKeep = sortedEntries.slice(-this.MAX_CACHE_ENTRIES);
        const newCache: Record<string, QueryCacheEntry> = {};
        entriesToKeep.forEach(([key, value]) => {
          newCache[key] = value;
        });
        this.setQueryCache(newCache);
      } else {
        this.setQueryCache(cache);
      }
    } catch (error) {
      console.warn("Failed to cache query result:", error);
    }
  }

  /**
   * Retrieve cached query result
   */
  getCachedQueryResult(sql: string, question: string): ExecuteResponse | null {
    try {
      const cache = this.getQueryCache();
      const cacheKey = this.generateQueryKey(sql, question);
      const entry = cache[cacheKey];

      if (!entry) {
        return null;
      }

      // Check if entry has expired
      if (Date.now() - entry.timestamp > entry.ttl) {
        this.removeCachedQuery(sql, question);
        return null;
      }

      return entry.data;
    } catch (error) {
      console.warn("Failed to retrieve cached query result:", error);
      return null;
    }
  }

  /**
   * Remove a specific cached query
   */
  removeCachedQuery(sql: string, question: string): void {
    try {
      const cache = this.getQueryCache();
      const cacheKey = this.generateQueryKey(sql, question);
      delete cache[cacheKey];
      this.setQueryCache(cache);
    } catch (error) {
      console.warn("Failed to remove cached query:", error);
    }
  }

  /**
   * Cache dashboard list
   */
  cacheDashboards(
    dashboards: Dashboard[],
    ttl: number = this.DEFAULT_TTL
  ): void {
    try {
      const entry: CacheEntry<Dashboard[]> = {
        data: dashboards,
        timestamp: Date.now(),
        ttl,
      };
      sessionStorage.setItem(this.DASHBOARD_CACHE_KEY, JSON.stringify(entry));
    } catch (error) {
      console.warn("Failed to cache dashboards:", error);
    }
  }

  /**
   * Retrieve cached dashboards
   */
  getCachedDashboards(): Dashboard[] | null {
    try {
      const cached = sessionStorage.getItem(this.DASHBOARD_CACHE_KEY);
      if (!cached) {
        return null;
      }

      const entry: CacheEntry<Dashboard[]> = JSON.parse(cached);

      // Check if entry has expired
      if (Date.now() - entry.timestamp > entry.ttl) {
        this.clearDashboardCache();
        return null;
      }

      return entry.data;
    } catch (error) {
      console.warn("Failed to retrieve cached dashboards:", error);
      return null;
    }
  }

  /**
   * Clear dashboard cache
   */
  clearDashboardCache(): void {
    try {
      sessionStorage.removeItem(this.DASHBOARD_CACHE_KEY);
    } catch (error) {
      console.warn("Failed to clear dashboard cache:", error);
    }
  }

  /**
   * Clear all query cache
   */
  clearQueryCache(): void {
    try {
      sessionStorage.removeItem(this.QUERY_CACHE_KEY);
    } catch (error) {
      console.warn("Failed to clear query cache:", error);
    }
  }

  /**
   * Clear all cache
   */
  clearAllCache(): void {
    this.clearQueryCache();
    this.clearDashboardCache();
  }

  /**
   * Get cache statistics
   */
  getCacheStats(): {
    queryCount: number;
    dashboardsCached: boolean;
    totalSize: number;
  } {
    try {
      const queryCache = this.getQueryCache();
      const dashboardCache = sessionStorage.getItem(this.DASHBOARD_CACHE_KEY);

      const queryCount = Object.keys(queryCache).length;
      const dashboardsCached = !!dashboardCache;

      // Estimate total size (rough approximation)
      const querySize = JSON.stringify(queryCache).length;
      const dashboardSize = dashboardCache ? dashboardCache.length : 0;
      const totalSize = querySize + dashboardSize;

      return {
        queryCount,
        dashboardsCached,
        totalSize,
      };
    } catch (error) {
      console.warn("Failed to get cache stats:", error);
      return {
        queryCount: 0,
        dashboardsCached: false,
        totalSize: 0,
      };
    }
  }

  /**
   * Generate a consistent cache key for SQL + question combination
   */
  private generateQueryKey(sql: string, question: string): string {
    // Create a simple hash of the SQL and question
    const combined = `${sql.trim().toLowerCase()}|${question
      .trim()
      .toLowerCase()}`;
    let hash = 0;
    for (let i = 0; i < combined.length; i++) {
      const char = combined.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return `query_${Math.abs(hash)}`;
  }

  /**
   * Get query cache from session storage
   */
  private getQueryCache(): Record<string, QueryCacheEntry> {
    try {
      const cached = sessionStorage.getItem(this.QUERY_CACHE_KEY);
      return cached ? JSON.parse(cached) : {};
    } catch (error) {
      console.warn("Failed to parse query cache:", error);
      return {};
    }
  }

  /**
   * Set query cache in session storage
   */
  private setQueryCache(cache: Record<string, QueryCacheEntry>): void {
    try {
      sessionStorage.setItem(this.QUERY_CACHE_KEY, JSON.stringify(cache));
    } catch (error) {
      console.warn("Failed to set query cache:", error);
    }
  }
}

// Export singleton instance
export const sessionCache = new SessionCache();
export default sessionCache;
