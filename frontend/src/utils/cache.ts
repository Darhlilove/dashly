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
    const startTime = performance.now();

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

      const cacheTime = performance.now() - startTime;

      // Log cache performance for automatic execution monitoring
      if (cacheTime > 50) {
        console.warn(
          `⚠️  Slow cache store: ${cacheTime.toFixed(2)}ms for ${
            result.row_count
          } rows`
        );
      } else {
        console.log(
          `💾 Cache stored: ${cacheTime.toFixed(2)}ms for ${
            result.row_count
          } rows`
        );
      }
    } catch (error) {
      const cacheTime = performance.now() - startTime;
      console.warn(
        `Failed to cache query result after ${cacheTime.toFixed(2)}ms:`,
        error
      );
    }
  }

  /**
   * Retrieve cached query result
   */
  getCachedQueryResult(sql: string, question: string): ExecuteResponse | null {
    const startTime = performance.now();

    try {
      const cache = this.getQueryCache();
      const cacheKey = this.generateQueryKey(sql, question);
      const entry = cache[cacheKey];

      if (!entry) {
        const cacheTime = performance.now() - startTime;
        console.log(`🔍 Cache miss: ${cacheTime.toFixed(2)}ms lookup`);
        return null;
      }

      // Check if entry has expired
      if (Date.now() - entry.timestamp > entry.ttl) {
        this.removeCachedQuery(sql, question);
        const cacheTime = performance.now() - startTime;
        console.log(`⏰ Cache expired: ${cacheTime.toFixed(2)}ms lookup`);
        return null;
      }

      const cacheTime = performance.now() - startTime;
      const ageMinutes = Math.round((Date.now() - entry.timestamp) / 60000);

      console.log(
        `✅ Cache hit: ${cacheTime.toFixed(2)}ms lookup, ${
          entry.data.row_count
        } rows, ${ageMinutes}min old`
      );

      // Log cache efficiency metrics for automatic execution monitoring
      if (cacheTime > 10) {
        console.warn(`⚠️  Slow cache retrieval: ${cacheTime.toFixed(2)}ms`);
      }

      return entry.data;
    } catch (error) {
      const cacheTime = performance.now() - startTime;
      console.warn(
        `Failed to retrieve cached query result after ${cacheTime.toFixed(
          2
        )}ms:`,
        error
      );
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
   * Get detailed cache performance metrics for automatic execution monitoring
   */
  getCachePerformanceMetrics(): {
    hitRate: number;
    averageAge: number;
    oldestEntry: number;
    newestEntry: number;
    totalRows: number;
    averageRowsPerQuery: number;
    cacheEfficiency: string;
  } {
    try {
      const queryCache = this.getQueryCache();
      const entries = Object.values(queryCache);
      const now = Date.now();

      if (entries.length === 0) {
        return {
          hitRate: 0,
          averageAge: 0,
          oldestEntry: 0,
          newestEntry: 0,
          totalRows: 0,
          averageRowsPerQuery: 0,
          cacheEfficiency: "No cache data",
        };
      }

      // Calculate cache metrics
      const ages = entries.map((entry) => now - entry.timestamp);
      const totalRows = entries.reduce(
        (sum, entry) => sum + (entry.data.row_count || 0),
        0
      );
      const averageAge = ages.reduce((sum, age) => sum + age, 0) / ages.length;
      const oldestEntry = Math.max(...ages);
      const newestEntry = Math.min(...ages);
      const averageRowsPerQuery = totalRows / entries.length;

      // Estimate hit rate based on cache age distribution
      const recentEntries = entries.filter(
        (entry) => now - entry.timestamp < 5 * 60 * 1000
      ); // Last 5 minutes
      const hitRate = recentEntries.length / entries.length;

      // Determine cache efficiency
      let cacheEfficiency = "Good";
      if (hitRate < 0.3) {
        cacheEfficiency = "Low hit rate";
      } else if (averageAge > 20 * 60 * 1000) {
        cacheEfficiency = "Stale entries";
      } else if (totalRows > 100000) {
        cacheEfficiency = "High memory usage";
      } else if (hitRate > 0.7 && averageAge < 10 * 60 * 1000) {
        cacheEfficiency = "Excellent";
      }

      return {
        hitRate: Math.round(hitRate * 100) / 100,
        averageAge: Math.round(averageAge / 60000), // Convert to minutes
        oldestEntry: Math.round(oldestEntry / 60000), // Convert to minutes
        newestEntry: Math.round(newestEntry / 60000), // Convert to minutes
        totalRows,
        averageRowsPerQuery: Math.round(averageRowsPerQuery),
        cacheEfficiency,
      };
    } catch (error) {
      console.warn("Failed to get cache performance metrics:", error);
      return {
        hitRate: 0,
        averageAge: 0,
        oldestEntry: 0,
        newestEntry: 0,
        totalRows: 0,
        averageRowsPerQuery: 0,
        cacheEfficiency: "Error calculating metrics",
      };
    }
  }

  /**
   * Log cache performance summary for automatic execution monitoring
   */
  logCachePerformance(): void {
    const metrics = this.getCachePerformanceMetrics();
    const stats = this.getCacheStats();

    console.group("📊 Cache Performance Summary");
    console.log(`🗄️  Entries: ${stats.queryCount}`);
    console.log(`🎯 Hit rate: ${(metrics.hitRate * 100).toFixed(1)}%`);
    console.log(`⏰ Average age: ${metrics.averageAge} minutes`);
    console.log(`📋 Total rows cached: ${metrics.totalRows.toLocaleString()}`);
    console.log(
      `📈 Avg rows/query: ${metrics.averageRowsPerQuery.toLocaleString()}`
    );
    console.log(`💾 Cache size: ${(stats.totalSize / 1024).toFixed(1)} KB`);
    console.log(`✨ Efficiency: ${metrics.cacheEfficiency}`);

    if (metrics.hitRate < 0.3) {
      console.warn(
        "⚠️  Low cache hit rate - consider adjusting TTL or query patterns"
      );
    }
    if (stats.totalSize > 1024 * 1024) {
      // 1MB
      console.warn(
        "⚠️  Large cache size - consider reducing TTL or max entries"
      );
    }
    if (metrics.oldestEntry > 30) {
      console.info(
        "💡 Old cache entries detected - automatic cleanup may be beneficial"
      );
    }

    console.groupEnd();
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
