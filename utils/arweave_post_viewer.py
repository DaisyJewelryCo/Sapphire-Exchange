"""
Arweave Post Viewer for development and debugging.
Provides utilities to inspect and visualize the master auction post before posting to Arweave.
"""
import json
from typing import Dict, Any, List
from datetime import datetime, timezone


class ArweavePostViewer:
    """Viewer for inspecting Arweave master post data."""
    
    def __init__(self, arweave_post_service):
        """Initialize viewer with reference to post service."""
        self.post_service = arweave_post_service
    
    def display_master_post_preview(self, verbose: bool = False) -> str:
        """
        Display a formatted preview of the master post.
        
        Args:
            verbose: If True, show full details including descriptions
            
        Returns:
            Formatted string of master post preview
        """
        output = []
        output.append("=" * 80)
        output.append("ARWEAVE MASTER POST PREVIEW")
        output.append("=" * 80)
        
        data = self.post_service.master_post_data
        output.append(f"Version: {data.get('version', 'N/A')}")
        output.append(f"Created: {data.get('created_at', 'N/A')}")
        output.append(f"Last Updated: {data.get('updated_at', 'N/A')}")
        output.append(f"Current TX ID: {self.post_service.master_post_tx_id or 'Not posted yet'}")
        output.append("")
        
        # Summary statistics
        summary = self.post_service.get_master_post_summary()
        if summary:
            output.append("SUMMARY STATISTICS")
            output.append("-" * 80)
            output.append(f"Total Auctions: {summary['total_auctions']}")
            output.append(f"Active Auctions: {summary['active_auctions']}")
            output.append(f"Finished Auctions: {summary['finished_auctions']}")
            output.append(f"Total Value: {summary['total_value_doge']:.2f} DOGE")
            output.append(f"Last Updated: {summary['last_updated']}")
            output.append("")
        
        # Active auctions
        active = self.post_service.get_active_auctions()
        if active:
            output.append(f"ACTIVE AUCTIONS ({len(active)})")
            output.append("-" * 80)
            for auction in active:
                output.extend(self._format_auction(auction, verbose))
                output.append("")
        
        # Finished auctions
        finished = self.post_service.get_finished_auctions()
        if finished:
            output.append(f"FINISHED AUCTIONS ({len(finished)})")
            output.append("-" * 80)
            for auction in finished:
                output.extend(self._format_auction(auction, verbose))
                output.append("")
        
        if not active and not finished:
            output.append("No auctions in master post")
            output.append("")
        
        output.append("=" * 80)
        return "\n".join(output)
    
    def _format_auction(self, auction, verbose: bool = False) -> List[str]:
        """Format a single auction for display."""
        lines = []
        
        if auction.sha_id:
            lines.append(f"SHA ID: {auction.sha_id[:16]}...")
        
        lines.append(f"Item ID: {auction.item_id}")
        lines.append(f"Title: {auction.title}")
        lines.append(f"Seller: {auction.seller_id[:8]}...")
        lines.append(f"Status: {auction.status}")
        lines.append(f"Starting Price: {auction.starting_price_doge} DOGE")
        lines.append(f"Current Bid: {auction.current_bid_doge} DOGE")
        
        if auction.current_bidder:
            lines.append(f"Current Bidder: {auction.current_bidder[:8]}...")
        
        lines.append(f"Auction Ends: {auction.auction_end}")
        
        # Nano wallet for bids
        if auction.auction_nano_address:
            lines.append(f"Nano Wallet for Bids: {auction.auction_nano_address[:20]}...")
            if auction.auction_nano_public_key:
                lines.append(f"  Public Key: {auction.auction_nano_public_key[:16]}...")
        

        
        if auction.winner:
            lines.append(f"Winner: {auction.winner[:8]}...")
            lines.append(f"Confirmed: {auction.confirmed_winner}")
            lines.append(f"Confirmations: {auction.confirmation_count}")
        
        if verbose and auction.description:
            lines.append(f"Description: {auction.description[:100]}...")
        
        return lines
    
    def display_master_post_json(self, pretty: bool = True) -> str:
        """
        Display the master post as JSON.
        
        Args:
            pretty: If True, format with indentation
            
        Returns:
            JSON string of master post
        """
        data = self.post_service.master_post_data.copy()
        
        # Convert auctions to dictionaries for JSON serialization
        if 'auctions' in data:
            auctions_dict = {}
            for item_id, auction in data['auctions'].items():
                if hasattr(auction, 'to_dict'):
                    auctions_dict[item_id] = auction.to_dict()
                else:
                    auctions_dict[item_id] = auction
            data['auctions'] = auctions_dict
        
        if pretty:
            return json.dumps(data, indent=2)
        else:
            return json.dumps(data)
    
    def display_ar_posting_info(self) -> str:
        """
        Display information about AR posting cost and balance needs.
        
        Returns:
            Formatted string with posting info
        """
        output = []
        output.append("=" * 80)
        output.append("ARWEAVE POSTING INFORMATION")
        output.append("=" * 80)
        
        summary = self.post_service.get_master_post_summary()
        
        if summary:
            output.append(f"Total Auctions: {summary['total_auctions']}")
            output.append(f"Active Auctions: {summary['active_auctions']}")
            output.append(f"Finished Auctions: {summary['finished_auctions']}")
            output.append("")
            
            # Estimate post size
            json_str = self.display_master_post_json(pretty=False)
            post_size_bytes = len(json_str.encode('utf-8'))
            post_size_kb = post_size_bytes / 1024
            
            output.append(f"Estimated Post Size: {post_size_kb:.2f} KB ({post_size_bytes} bytes)")
            output.append("")
            
            output.append("AR COST INFORMATION")
            output.append("-" * 80)
            output.append("Fixed Cost per Post: 0.05 AR")
            output.append("Estimated Total: 0.05 AR")
            output.append("")
            
            output.append("REQUIRED AR BALANCE")
            output.append("-" * 80)
            output.append("Minimum: 0.05 AR")
            output.append("Recommended: 0.10 AR (for multiple posts)")
            output.append("")
        
        output.append("=" * 80)
        return "\n".join(output)
    
    def display_nano_wallet_info(self) -> str:
        """
        Display information about auction Nano wallets.
        
        Returns:
            Formatted string with wallet info
        """
        output = []
        output.append("=" * 80)
        output.append("AUCTION NANO WALLET INFORMATION")
        output.append("=" * 80)
        
        active = self.post_service.get_active_auctions()
        
        if not active:
            output.append("No active auctions with Nano wallets")
            output.append("=" * 80)
            return "\n".join(output)
        
        output.append(f"Total Active Auctions: {len(active)}")
        output.append("")
        
        wallets_with_addresses = [a for a in active if a.auction_nano_address]
        output.append(f"Auctions with Nano Wallets: {len(wallets_with_addresses)}")
        output.append("")
        
        if wallets_with_addresses:
            output.append("NANO WALLET ADDRESSES (organized by SHA ID)")
            output.append("-" * 80)
            for auction in wallets_with_addresses:
                output.append(f"SHA ID: {auction.sha_id[:16]}...")
                output.append(f"Item: {auction.item_id[:8]}... ({auction.title[:30]}...)")
                output.append(f"  Nano Address: {auction.auction_nano_address}")
                output.append(f"  Nano Public Key: {auction.auction_nano_public_key[:20]}...")
                output.append(f"  Current Bid: {auction.current_bid_usdc} USDC")
                output.append("")
        
        output.append("=" * 80)
        return "\n".join(output)
    
    def display_auction_summary_table(self) -> str:
        """
        Display auctions as a summary table, organized by SHA ID.
        
        Returns:
            Formatted table string
        """
        output = []
        output.append("=" * 140)
        output.append("AUCTION SUMMARY TABLE (organized by RSA Fingerprint)")
        output.append("=" * 140)
        
        # Header - RSA fingerprint is the primary ID
        header = f"{'RSA Fingerprint':<20} | {'Title':<20} | {'Status':<10} | {'Current Bid':<12} | {'Nano Wallet':<20} | {'End Time':<20}"
        output.append(header)
        output.append("-" * 140)
        
        # Rows
        all_auctions = list(self.post_service.master_post_data['auctions'].items())
        
        if not all_auctions:
            output.append("No auctions in master post")
        else:
            for rsa_fingerprint, auction in all_auctions:
                fp = rsa_fingerprint[:18] if rsa_fingerprint else 'N/A'
                title = auction.title[:18] if hasattr(auction, 'title') else 'N/A'
                status = auction.status[:9] if hasattr(auction, 'status') else 'N/A'
                current = f"{auction.current_bid_doge[:10]}" if hasattr(auction, 'current_bid_doge') else 'N/A'
                wallet = auction.auction_nano_address[:18] if hasattr(auction, 'auction_nano_address') and auction.auction_nano_address else 'None'
                end_time = auction.auction_end[:19] if hasattr(auction, 'auction_end') else 'N/A'
                
                row = f"{fp:<20} | {title:<20} | {status:<10} | {current:<12} | {wallet:<20} | {end_time}"
                output.append(row)
        
        output.append("=" * 140)
        return "\n".join(output)
    
    def save_post_to_file(self, filename: str, include_preview: bool = True) -> bool:
        """
        Save the master post to a JSON file for inspection.
        
        Args:
            filename: File path to save to
            include_preview: If True, include human-readable preview
            
        Returns:
            True if saved successfully
        """
        try:
            content = []
            
            if include_preview:
                content.append(self.display_master_post_preview())
                content.append("\n\n")
                content.append(self.display_master_post_json(pretty=True))
            else:
                content.append(self.display_master_post_json(pretty=True))
            
            with open(filename, 'w') as f:
                f.write("\n".join(content))
            
            print(f"Master post saved to {filename}")
            return True
        except Exception as e:
            print(f"Error saving post to file: {e}")
            return False


def view_master_post(arweave_post_service, output_type: str = 'preview') -> str:
    """
    Quick function to view the master post in various formats.
    
    Args:
        arweave_post_service: The ArweavePostService instance
        output_type: 'preview', 'json', 'table', 'wallets', or 'ar_info'
        
    Returns:
        Formatted string for the requested output type
    """
    viewer = ArweavePostViewer(arweave_post_service)
    
    if output_type == 'preview':
        return viewer.display_master_post_preview(verbose=False)
    elif output_type == 'preview_verbose':
        return viewer.display_master_post_preview(verbose=True)
    elif output_type == 'json':
        return viewer.display_master_post_json(pretty=True)
    elif output_type == 'table':
        return viewer.display_auction_summary_table()
    elif output_type == 'wallets':
        return viewer.display_nano_wallet_info()
    elif output_type == 'ar_info':
        return viewer.display_ar_posting_info()
    else:
        return f"Unknown output type: {output_type}"
