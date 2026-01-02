# Repository Structure

## 📂 Main Directories

### `/database/` - Product Research Database
All database files, tools, and exports for product research.

### `/fusion-mcp-server/` - Fusion 360 MCP Server
MCP server for Fusion 360 integration.

### `/fusion-addin/` - Fusion 360 Add-in
Python add-in for Fusion 360.

### `/fusion-patterns/` - Fusion 360 Patterns & Examples
Documentation and examples for common Fusion 360 patterns.

### `/japanese-watch-box/` - Japanese Watch Box Project
Specific product project files.

### `/rustic-wedding-memory-box/` - Wedding Memory Box Project
Specific product project files.

### `/wavy-shelf-project/` - Wavy Shelf Project
Specific product project files.

### `/woodworking-calculator/` - Woodworking Calculator
Tools for woodworking calculations.

### `/archive/` - Archived Research Files
Old analysis files, scripts, and reports from initial research phase.

## 📄 Root Files

### Database & Analysis
- `DATABASE_INDEX.md` - **START HERE** - Main database guide
- `DATABASE_USAGE_GUIDE.md` - Quick start guide
- `DATABASE_REPORT.md` - Analysis report
- `DATABASE_README.md` - Technical docs
- `ORGANIZATION_COMPLETE.md` - Organization summary

### Project Documentation
- `fusion-mcp-spec.md` - Fusion MCP specification
- `product-analysis-framework.md` - Analysis framework
- `SETUP.md` - Setup instructions

## 🗃️ Archived Files

All initial research files (JSON, analysis reports, collection scripts) have been:
1. Imported into the SQLite database
2. Moved to `/archive/` for reference
3. No longer needed for daily use

The database (`database/product_research.db`) now contains all this data in a structured, queryable format.
