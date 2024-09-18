import threading
import time
import sys
from collections import deque
from tabulate import tabulate
from datetime import datetime

class Order:
    def __init__(self, order_number, order_type):
        self.order_number = order_number
        self.type = order_type  # 'normal' or 'VIP'
        self.status = "PENDING"
        self.creation_time = datetime.now()  # Track order creation time
        self.start_time = None  # To track processing start time
        self.end_time = None    # To track processing end time

    def __str__(self):
        return f"Order {self.order_number} [{self.type.upper()}] - {self.status}"

class Bot(threading.Thread):
    def __init__(self, bot_id, controller):
        super().__init__()
        self.bot_id = bot_id
        self.controller = controller
        self.current_order = None
        self.stop_event = threading.Event()

    def run(self):
        while not self.stop_event.is_set():
            order = self.controller.get_next_order()
            if order:
                self.current_order = order
                order.status = "PROCESSING"
                order.start_time = datetime.now()  # Record processing start time
                print(f"\n[Bot {self.bot_id}] Started processing {order}")
                start_time = time.time()
                while time.time() - start_time < 10:
                    if self.stop_event.is_set():
                        print(f"\n[Bot {self.bot_id}] Stopping. Returning {order} to PENDING.")
                        order.status = "PENDING"
                        order.start_time = None
                        self.current_order = None
                        return
                    time.sleep(1)  # Check every second if stop is requested
                order.status = "COMPLETE"
                order.end_time = datetime.now()  # Set end time on completion
                print(f"\n[Bot {self.bot_id}] Completed {order}")
                self.current_order = None
            else:
                time.sleep(1)  # Wait before checking again if no orders are pending

    def stop(self):
        self.stop_event.set()
        if self.current_order:
            print(f"\n[Bot {self.bot_id}] is being stopped while processing {self.current_order}")
        self.join()

class OrderController:
    def __init__(self):
        self.order_lock = threading.Lock()
        self.orders = []  # List of all orders
        self.pending_orders = deque()  # Queue for pending orders
        self.order_number = 0
        self.bots = []
        self.bot_id_counter = 1

    def add_order(self, order_type):
        with self.order_lock:
            self.order_number += 1
            new_order = Order(self.order_number, order_type)
            self.orders.append(new_order)
            
            if order_type.upper() == 'VIP':
                # Find the position after the last VIP order in the pending queue
                index = 0
                for i, order in enumerate(self.pending_orders):
                    if order.type.upper() != 'VIP':  # Stop when you reach the first non-VIP order
                        break
                    index = i + 1
                self.pending_orders.insert(index, new_order)  # Insert VIP order at the found position
            else:
                # Normal orders always go to the end of the queue
                self.pending_orders.append(new_order)
            
            print(f"\n[System] Added {new_order}")

    def get_next_order(self):
        with self.order_lock:
            if self.pending_orders:
                order = self.pending_orders.popleft()
                return order
            else:
                return None

    def add_bot(self):
        with self.order_lock:
            bot = Bot(self.bot_id_counter, self)
            self.bot_id_counter += 1
            self.bots.append(bot)
            bot.start()
            print(f"\n[System] Added Bot {bot.bot_id}")
            return bot.bot_id

    def remove_bot(self):
        with self.order_lock:
            if not self.bots:
                print("\n[System] No bots to remove.")
                return
            bot = self.bots.pop()
            bot.stop()
            print(f"\n[System] Removed Bot {bot.bot_id}")

    def view_orders(self):
        while True:
            print("\n--- View Orders ---")
            print("1. All Orders")
            print("2. PENDING Orders")
            print("3. PROCESSING Orders")
            print("4. COMPLETE Orders")
            print("5. Back to Main Menu")
            choice = input("Select an option to view orders: ").strip()

            if choice == '1':
                self.display_orders("ALL")
            elif choice == '2':
                self.display_orders("PENDING")
            elif choice == '3':
                self.display_orders("PROCESSING")
            elif choice == '4':
                self.display_orders("COMPLETE")
            elif choice == '5':
                break
            else:
                print("Invalid choice. Please select a valid option.")

    def display_orders(self, filter_status):
        with self.order_lock:
            if not self.orders:
                print("\n[System] No orders have been placed yet.")
                return

            filtered_orders = []
            for order in self.orders:
                if filter_status == "ALL" or order.status == filter_status:
                    if order.status == "PENDING":
                        waiting_time = (datetime.now() - order.creation_time).total_seconds()
                        waiting_time_str = f"{int(waiting_time)}s"
                        start_time_str = "-"
                        end_time_str = "-"
                    elif order.status == "PROCESSING":
                        waiting_time = (order.start_time - order.creation_time).total_seconds()
                        waiting_time_str = f"{int(waiting_time)}s"
                        start_time_str = order.start_time.strftime('%Y-%m-%d %H:%M:%S') if order.start_time else "-"
                        end_time_str = "-"
                    elif order.status == "COMPLETE":
                        waiting_time = (order.start_time - order.creation_time).total_seconds() if order.start_time else 0
                        waiting_time_str = f"{int(waiting_time)}s"
                        start_time_str = order.start_time.strftime('%Y-%m-%d %H:%M:%S') if order.start_time else "-"
                        end_time_str = order.end_time.strftime('%Y-%m-%d %H:%M:%S') if order.end_time else "-"
                    else:
                        waiting_time_str = "-"
                        start_time_str = "-"
                        end_time_str = "-"
                    
                    if order.status == "PROCESSING" and order.start_time:
                        elapsed = (datetime.now() - order.start_time).total_seconds()
                        progress = min(elapsed / 10, 1)  # Ensure it doesn't exceed 100%
                        progress_bar = generate_progress_bar(progress)
                        percentage = int(progress * 100)
                        filtered_orders.append([
                            order.order_number,
                            order.type.upper(),
                            order.status,
                            f"{progress_bar} {percentage}%",
                            start_time_str,
                            end_time_str,
                            waiting_time_str
                        ])
                    else:
                        filtered_orders.append([
                            order.order_number,
                            order.type.upper(),
                            order.status,
                            "-",
                            start_time_str,
                            end_time_str,
                            waiting_time_str
                        ])

            if not filtered_orders:
                print(f"\n[System] No orders found with status '{filter_status}'.")
                return

            headers = ["Order #", "Type", "Status", "Progress", "Start Time", "End Time", "Waiting Time"]
            print("\n" + tabulate(filtered_orders, headers=headers, tablefmt="grid"))

    def shutdown(self):
        print("\n[System] Shutting down all bots...")
        for bot in self.bots:
            bot.stop()
        print("[System] All bots have been shut down.")

def generate_progress_bar(progress, length=20):
    """
    Generates a simple text-based progress bar using ASCII characters.
    :param progress: Float between 0 and 1 indicating progress.
    :param length: The length of the progress bar.
    :return: A string representing the progress bar.
    """
    filled_length = int(length * progress)
    bar = '#' * filled_length + '-' * (length - filled_length)
    return f"[{bar}]"

def print_menu():
    print("\n--- McOrder CLI ---")
    print("1. New Normal Order")
    print("2. New VIP Order")
    print("3. Add Bot")
    print("4. Remove Bot")
    print("5. View Orders")
    print("6. Exit")
    print("--------------------")

def main():
    controller = OrderController()

    try:
        while True:
            print_menu()
            choice = input("Enter your choice: ").strip()

            if choice == '1':
                controller.add_order('normal')
            elif choice == '2':
                controller.add_order('VIP')
            elif choice == '3':
                controller.add_bot()
            elif choice == '4':
                controller.remove_bot()
            elif choice == '5':
                controller.view_orders()
            elif choice == '6':
                print("\n[System] Exiting...")
                break
            else:
                print("Invalid choice. Please select a valid option.")
    except KeyboardInterrupt:
        print("\n[System] Interrupted by user.")
    finally:
        controller.shutdown()
        sys.exit()

if __name__ == "__main__":
    main()
