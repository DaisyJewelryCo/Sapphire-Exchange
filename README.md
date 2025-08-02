# Sapphire Exchange

A decentralized auction platform built on Arweave and Nano, enabling users to list, bid on, and purchase items with secure blockchain transactions.

## Features

- **Decentralized Storage**: All item data is stored on the Arweave blockchain for permanence and immutability.
- **Nano Integration**: Fast, feeless Nano transactions for bidding and purchasing.
- **Secure Wallet Management**: Built-in wallet generation and management.
- **Auction System**: Support for timed auctions with automatic finalization.

## Prerequisites

- Python 3.7+
- pip (Python package manager)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd Sapphire_Exchange
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your environment variables by creating a `.env` file in the project root:
   ```
   ARWEAVE_GATEWAY_URL=https://arweave.net
   ARWEAVE_WALLET_FILE=wallet.json
   NANO_NODE_URL=https://mynano.ninja/api
   NANO_REPRESENTATIVE=nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3
   ```

## Usage

1. Run the application:
   ```bash
   python app.py
   ```

2. The application will demonstrate:
   - Creating a seller wallet
   - Creating a buyer wallet
   - Listing a new item for auction
   - Placing a bid on the item
   - Finalizing the auction

## Project Structure

- `app.py`: Main application with the AuctionHouse class and command-line interface
- `arweave_utils.py`: Handles interactions with the Arweave blockchain
- `nano_utils.py`: Manages Nano wallet and transaction functionality
- `.env`: Configuration file for environment variables
- `requirements.txt`: Python dependencies

## How It Works

1. **Item Listing**: Sellers create listings that are stored on Arweave, including item details and auction parameters.
2. **Bidding**: Buyers place bids by sending Nano to an escrow address.
3. **Auction Finalization**: When the auction ends, the highest bidder receives the item, and the seller receives the payment.
4. **Ownership Transfer**: The item's ownership is updated on the blockchain.

## Security Notes

- Keep your wallet files (wallet.json) secure and never share them.
- For production use, implement proper key management and security practices.
- Test with small amounts first when using real cryptocurrency.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
