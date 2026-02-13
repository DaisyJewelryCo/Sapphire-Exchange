"""
Arweave Auction Post Viewer and Generator for development.
Provides utilities to preview and inspect Arweave auction post data before posting.
"""
import json
from typing import Dict, Any, List
from datetime import datetime, timezone


class ArweaveAuctionViewer:
    """Viewer for previewing Arweave auction post data before posting."""
    
    def __init__(self, arweave_post_service):
        """Initialize viewer with reference to post service."""
        self.post_service = arweave_post_service
    
    def preview_auction_post(self, post_data: Dict[str, Any], verbose: bool = False) -> str:
        """
        Display a formatted preview of an auction post or inventory post before posting.
        
        Args:
            post_data: The post data dictionary
            verbose: If True, show full details
            
        Returns:
            Formatted string of post preview
        """
        output = []
        output.append("=" * 100)
        
        # Determine post type
        post_type = post_data.get('type', 'auction')
        
        if post_type == 'inventory':
            output.append("ARWEAVE INVENTORY POST PREVIEW (Before Posting to Network)")
        else:
            output.append("ARWEAVE AUCTION POST PREVIEW (Before Posting to Network)")
        output.append("=" * 100)
        output.append("")
        
        # Post metadata
        output.append("POST METADATA")
        output.append("-" * 100)
        output.append(f"Type: {post_type.upper()}")
        output.append(f"Version: {post_data.get('version', 'N/A')}")
        output.append(f"Sequence Number: {post_data.get('sequence', 'N/A')}")
        output.append(f"Posted By: {post_data.get('posted_by', 'N/A')[:8]}...")
        output.append(f"Created At: {post_data.get('created_at', 'N/A')}")
        
        if post_type == 'inventory':
            output.append(f"Seller Nano Address: {post_data.get('seller_nano_address', 'N/A')[:20]}...")
            output.append(f"Seller Arweave Address: {post_data.get('seller_arweave_address', 'N/A')[:16]}...")
            if post_data.get('previous_inventory_uri'):
                output.append(f"Previous Inventory URI: {post_data.get('previous_inventory_uri')[:16]}...")
        output.append("")
        
        # Handle inventory posts
        if post_type == 'inventory':
            items = post_data.get('items', [])
            output.append("INVENTORY ITEMS")
            output.append("-" * 100)
            output.append(f"Total Items: {post_data.get('item_count', len(items))}")
            output.append("")
            
            if items:
                for i, item in enumerate(items, 1):
                    output.append(f"  [{i}] {item.get('title', 'N/A')[:50]}")
                    output.append(f"      Item ID: {item.get('item_id', 'N/A')[:8]}...")
                    output.append(f"      SHA ID: {item.get('sha_id', 'N/A')[:16]}...")
                    output.append(f"      Status: {item.get('status', 'N/A')}")
                    output.append(f"      Starting Price (USDC): {item.get('starting_price_usdc', 'N/A')}")
                    if verbose and item.get('description'):
                        output.append(f"      Description: {item.get('description')[:100]}...")
                    output.append("")
            output.append("")
        else:
            # Handle auction posts
            auction = post_data.get('auction', {})
            if auction:
                output.append("TOP SECTION: CURRENT AUCTION DETAILS")
                output.append("-" * 100)
                output.append(f"SHA ID: {auction.get('sha_id', 'N/A')[:16]}...")
                output.append(f"Item ID: {auction.get('item_id', 'N/A')[:8]}...")
                output.append(f"Title: {auction.get('title', 'N/A')}")
                output.append(f"Seller: {auction.get('seller_id', 'N/A')[:8]}...")
                output.append(f"Status: {auction.get('status', 'N/A')}")
                output.append("")
                
                if verbose and auction.get('description'):
                    output.append(f"Description: {auction.get('description')[:200]}...")
                    output.append("")
                
                output.append(f"Starting Price: {auction.get('starting_price_doge', 'N/A')} DOGE")
                output.append(f"Current Bid: {auction.get('current_bid_doge', 'N/A')} DOGE")
                output.append(f"Current Bidder: {auction.get('current_bidder', 'None')[:8] if auction.get('current_bidder') else 'None'}...")
                output.append(f"Auction Ends: {auction.get('auction_end', 'N/A')}")
                output.append("")
                
                output.append("NANO WALLET INFO (for bids)")
                output.append("-" * 100)
                output.append(f"Nano Address: {auction.get('auction_nano_address', 'N/A')[:20]}...")
                output.append(f"Nano Public Key: {auction.get('auction_nano_public_key', 'N/A')[:20]}...")
                output.append("")
            
            # Bottom section: Expiring auctions
            expiring_auctions = post_data.get('expiring_auctions', [])
            output.append("BOTTOM SECTION: AUCTIONS EXPIRING IN NEXT 24 HOURS")
            output.append("-" * 100)
            
            if expiring_auctions:
                output.append(f"Total Expiring Auctions: {len(expiring_auctions)}")
                output.append("")
                
                for i, exp_auction in enumerate(expiring_auctions, 1):
                    output.append(f"  [{i}] {exp_auction.get('title', 'N/A')[:40]}")
                    output.append(f"      Item ID: {exp_auction.get('item_id', 'N/A')[:8]}...")
                    output.append(f"      SHA ID: {exp_auction.get('sha_id', 'N/A')[:16]}...")
                    output.append(f"      Current Bid: {exp_auction.get('current_bid_doge', 'N/A')} DOGE")
                    output.append(f"      Current Bidder: {exp_auction.get('current_bidder', 'None')[:8] if exp_auction.get('current_bidder') else 'None'}...")
                    output.append(f"      Top Bidder Nano: {exp_auction.get('top_bidder_nano_address', 'N/A')[:20]}...")
                    output.append(f"      Expires: {exp_auction.get('auction_end', 'N/A')}")
                    output.append("")
            else:
                output.append("No auctions expiring in next 24 hours")
                output.append("")
        
        # Posting cost estimate
        output.append("POSTING COST ESTIMATE")
        output.append("-" * 100)
        post_size_bytes = len(json.dumps(post_data).encode('utf-8'))
        estimated_cost_ar = (post_size_bytes / 1000) * 0.001  # Rough estimate
        output.append(f"Estimated Post Size: {post_size_bytes:,} bytes")
        output.append(f"Estimated AR Cost: ~{estimated_cost_ar:.6f} AR (varies with network)")
        output.append("")
        
        output.append("=" * 100)
        return "\n".join(output)
    
    def preview_auction_post_json(self, post_data: Dict[str, Any], pretty: bool = True) -> str:
        """
        Display the post as JSON.
        
        Args:
            post_data: The post data dictionary
            pretty: If True, format with indentation
            
        Returns:
            JSON string
        """
        if pretty:
            return json.dumps(post_data, indent=2)
        else:
            return json.dumps(post_data)
    
    def preview_post_structure(self, post_data: Dict[str, Any]) -> str:
        """
        Display the structure and hierarchy of the post.
        
        Args:
            post_data: The post data dictionary
            
        Returns:
            Formatted structure visualization
        """
        output = []
        output.append("=" * 80)
        output.append("ARWEAVE POST STRUCTURE")
        output.append("=" * 80)
        output.append("")
        
        output.append("Post Structure:")
        output.append("├── version: " + str(post_data.get('version')))
        output.append("├── sequence: " + str(post_data.get('sequence')))
        output.append("├── created_at: " + str(post_data.get('created_at')))
        output.append("├── posted_by: " + str(post_data.get('posted_by', 'N/A')[:8]))
        output.append("│")
        output.append("├── auction (TOP SECTION)")
        auction = post_data.get('auction', {})
        output.append("│   ├── sha_id: " + str(auction.get('sha_id', 'N/A')[:16]))
        output.append("│   ├── item_id: " + str(auction.get('item_id')))
        output.append("│   ├── title: " + str(auction.get('title', 'N/A')[:30]))
        output.append("│   ├── seller_id: " + str(auction.get('seller_id', 'N/A')[:8]))
        output.append("│   ├── starting_price_doge: " + str(auction.get('starting_price_doge')))
        output.append("│   ├── current_bid_doge: " + str(auction.get('current_bid_doge')))
        output.append("│   ├── current_bidder: " + str(auction.get('current_bidder', 'None')[:8] if auction.get('current_bidder') else 'None'))
        output.append("│   ├── auction_end: " + str(auction.get('auction_end')))
        output.append("│   ├── auction_nano_address: " + str(auction.get('auction_nano_address', 'N/A')[:20]))
        output.append("│   └── auction_nano_public_key: " + str(auction.get('auction_nano_public_key', 'N/A')[:20]))
        output.append("│")
        output.append("└── expiring_auctions (BOTTOM SECTION)")
        expiring = post_data.get('expiring_auctions', [])
        output.append(f"    ├── count: {len(expiring)}")
        for i, exp in enumerate(expiring[:3]):
            prefix = "    ├── " if i < len(expiring) - 1 else "    └── "
            output.append(f"{prefix}[{i}] {exp.get('title', 'N/A')[:30]}")
        if len(expiring) > 3:
            output.append(f"    └── ... and {len(expiring) - 3} more")
        
        output.append("")
        output.append("=" * 80)
        return "\n".join(output)
    
    def preview_search_results(self, posts: List[Dict[str, Any]]) -> str:
        """
        Display search results from Arweave.
        
        Args:
            posts: List of post data from search
            
        Returns:
            Formatted search results
        """
        output = []
        output.append("=" * 100)
        output.append("ARWEAVE SEARCH RESULTS")
        output.append("=" * 100)
        output.append("")
        
        if not posts:
            output.append("No posts found matching search criteria")
            output.append("")
        else:
            output.append(f"Found {len(posts)} posts")
            output.append("")
            
            for i, post in enumerate(posts, 1):
                output.append(f"[{i}] Sequence: {post.get('sequence')}")
                
                auction = post.get('auction', {})
                output.append(f"    Title: {auction.get('title', 'N/A')}")
                output.append(f"    SHA ID: {auction.get('sha_id', 'N/A')[:16]}...")
                output.append(f"    Current Bid: {auction.get('current_bid_doge', 'N/A')} DOGE")
                output.append(f"    Expires: {auction.get('auction_end', 'N/A')}")
                
                expiring_count = len(post.get('expiring_auctions', []))
                output.append(f"    Expiring Auctions Listed: {expiring_count}")
                output.append("")
        
        output.append("=" * 100)
        return "\n".join(output)
    
    def save_post_to_file(self, post_data: Dict[str, Any], filename: str) -> bool:
        """
        Save post preview to file for inspection.
        
        Args:
            post_data: The post data
            filename: File path to save to
            
        Returns:
            True if saved successfully
        """
        try:
            content = []
            content.append(self.preview_auction_post(post_data, verbose=True))
            content.append("\n\n" + "=" * 100)
            content.append("RAW JSON DATA")
            content.append("=" * 100 + "\n\n")
            content.append(self.preview_auction_post_json(post_data, pretty=True))
            
            with open(filename, 'w') as f:
                f.write("\n".join(content))
            
            print(f"Post preview saved to {filename}")
            return True
        except Exception as e:
            print(f"Error saving post to file: {e}")
            return False


def view_auction_post_preview(arweave_post_service, post_data: Dict[str, Any], 
                             output_type: str = 'preview') -> str:
    """
    Quick function to preview auction post in various formats.
    
    Args:
        arweave_post_service: The ArweavePostService instance
        post_data: The post data to preview
        output_type: 'preview', 'json', 'structure', or 'cost'
        
    Returns:
        Formatted string for the requested output type
    """
    viewer = ArweaveAuctionViewer(arweave_post_service)
    
    if output_type == 'preview':
        return viewer.preview_auction_post(post_data, verbose=False)
    elif output_type == 'preview_verbose':
        return viewer.preview_auction_post(post_data, verbose=True)
    elif output_type == 'json':
        return viewer.preview_auction_post_json(post_data, pretty=True)
    elif output_type == 'structure':
        return viewer.preview_post_structure(post_data)
    else:
        return viewer.preview_auction_post(post_data, verbose=False)
